# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import requests

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# The Profolio API token is NEVER stored in code: it lives only in Settings
# (ir.config_parameter bayut_lead_integration.bayut_api_key / bayut_listing_api_key).
BAYUT_API_BASE = "https://api.bayut.com/v1"
ACTIVE_PORTAL = "bayut"       # listings scope: Bayut only for now (dubizzle later)
DEFAULT_LEADS_API_URL = BAYUT_API_BASE + "/leads"
DEFAULT_LISTING_API_URL = BAYUT_API_BASE + "/properties"
OLD_LISTING_API_URLS = ("https://api.bayut.com/v1/listings",)

# Old placeholder value stored in existing databases -> replaced by DEFAULT_LEADS_API_URL at runtime
PLACEHOLDER_LEADS_HOSTS = ("leads-api.bayut.com",)

# Lead pull (backup to the push webhook)
PULL_CHANNELS = ("phone", "whatsapp")
PULL_PER_PAGE = 100
PULL_LOOKBACK_DAYS = 3        # re-pull recent days: Bayut backfills enriched data after creation
PULL_INITIAL_DAYS = 60        # first run: recover leads received before the webhook was registered
RATE_LIMIT_MAX_RETRIES = 2
RATE_LIMIT_MAX_WAIT = 60      # seconds

# Push API (Bayut / dubizzle -> Odoo): portal -> (signature header, secret config parameter)
PUSH_PORTALS = {
    "bayut": ("X-Bayut-Signature", "bayut_lead_integration.bayut_push_secret"),
    "dubizzle": ("X-dubizzle-Signature", "bayut_lead_integration.dubizzle_push_secret"),
}

INTENT_SIGNAL_TYPES = {"phone_view", "sms_click"}
INTENT_SIGNAL_NOTE = _(
    "Note: This is an intent signal (user viewed phone number or clicked SMS on Bayut), not a full lead."
)


class BayutConnector(models.Model):
    _name = "bayut.connector"
    _description = "Bayut Leads & Listings API Connector"
    _rec_name = "name"

    name = fields.Char(
        string="Connector Name",
        default="Bayut Profolio Connector",
        required=True,
    )

    # Editable Configuration Fields (Synced with ir.config_parameter)
    api_url = fields.Char(
        string="Bayut Leads API URL",
        default=DEFAULT_LEADS_API_URL,
        help="Endpoint URL for fetching leads from Bayut.",
    )
    api_key = fields.Char(
        string="Bayut Leads API Key",
        help="Bearer API token used for Bayut Leads API authentication.",
    )
    listing_api_url = fields.Char(
        string="Bayut Listing API URL",
        default=DEFAULT_LISTING_API_URL,
        help="Endpoint URL for pushing/updating property listings on Bayut Profolio.",
    )
    listing_api_key = fields.Char(
        string="Bayut Listing API Key",
        help="Bearer API token provided by the Bayut team for Profolio Listing integration.",
    )
    default_team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Default Sales Team",
    )
    default_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Default Salesperson",
        domain=[("share", "=", False)],
    )
    sync_interval = fields.Integer(
        string="Sync Interval (Minutes)",
        default=10,
    )

    # Read-Only Status & Feed Endpoints
    last_sync = fields.Datetime(
        string="Last Leads Sync",
        readonly=True,
        help="Timestamp of the last successful Bayut leads synchronization.",
    )
    last_listing_sync = fields.Datetime(
        string="Last Listings Sync",
        readonly=True,
        help="Timestamp of the last Bayut listings synchronization.",
    )
    xml_feed_url = fields.Char(
        string="Profolio XML Feed URL",
        compute="_compute_endpoints_and_counts",
    )
    json_feed_url = fields.Char(
        string="Profolio JSON Feed URL",
        compute="_compute_endpoints_and_counts",
    )
    webhook_url = fields.Char(
        string="Bayut Push API URL",
        compute="_compute_endpoints_and_counts",
        help="Give this URL to support@bayut.com to receive Bayut call & WhatsApp leads in real time.",
    )
    dubizzle_webhook_url = fields.Char(
        string="dubizzle Push API URL",
        compute="_compute_endpoints_and_counts",
        help="Give this URL to ps-reply@dubizzle.com to receive dubizzle WhatsApp leads in real time.",
    )

    log_ids = fields.One2many(
        comodel_name="bayut.sync.log",
        inverse_name="connector_id",
        string="Sync Logs",
        readonly=True,
    )
    log_count = fields.Integer(
        string="Sync Log Count",
        compute="_compute_endpoints_and_counts",
    )
    listing_count = fields.Integer(
        string="Listings Count",
        compute="_compute_endpoints_and_counts",
    )
    published_listing_count = fields.Integer(
        string="Published Listings",
        compute="_compute_endpoints_and_counts",
    )
    bayut_lead_count = fields.Integer(
        string="Bayut Leads Count",
        compute="_compute_endpoints_and_counts",
    )

    def _compute_endpoints_and_counts(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
        Listing = self.env["bayut.listing"].sudo()
        # Count leads with the user's own access so the button matches what the list shows
        Lead = self.env["crm.lead"]
        total_listings = Listing.search_count([])
        pub_listings = Listing.search_count([("state", "=", "published")])
        total_leads = Lead.search_count([("bayut_lead_id", "!=", False)])

        for rec in self:
            rec.xml_feed_url = f"{base_url}/bayut/feed/listings.xml"
            rec.json_feed_url = f"{base_url}/bayut/feed/listings.json"
            rec.webhook_url = f"{base_url}/bayut/webhook/leads"
            rec.dubizzle_webhook_url = f"{base_url}/dubizzle/webhook/leads"
            rec.log_count = len(rec.log_ids)
            rec.listing_count = total_listings
            rec.published_listing_count = pub_listings
            rec.bayut_lead_count = total_leads

    @api.model
    def _get_connector(self):
        """Return the singleton Bayut connector record, creating it and syncing params if needed."""
        connector = self.sudo().search([], order="id asc", limit=1)
        params = self.env["ir.config_parameter"].sudo()
        if not connector:
            connector = self.sudo().create({
                "name": "Bayut Profolio Connector",
                "api_url": params.get_param("bayut_lead_integration.bayut_api_url") or DEFAULT_LEADS_API_URL,
                "api_key": params.get_param("bayut_lead_integration.bayut_api_key") or "",
                "listing_api_url": params.get_param("bayut_lead_integration.bayut_listing_api_url") or DEFAULT_LISTING_API_URL,
                "listing_api_key": params.get_param("bayut_lead_integration.bayut_listing_api_key") or "",
            })
        return connector

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_param_sync"):
            params = self.env["ir.config_parameter"].sudo()
            for rec in self:
                if "api_url" in vals:
                    params.set_param("bayut_lead_integration.bayut_api_url", rec.api_url or DEFAULT_LEADS_API_URL)
                if "api_key" in vals:
                    params.set_param("bayut_lead_integration.bayut_api_key", rec.api_key or "")
                if "listing_api_url" in vals:
                    params.set_param("bayut_lead_integration.bayut_listing_api_url", rec.listing_api_url or DEFAULT_LISTING_API_URL)
                if "listing_api_key" in vals:
                    params.set_param("bayut_lead_integration.bayut_listing_api_key", rec.listing_api_key or "")
                if "default_team_id" in vals:
                    params.set_param("bayut_lead_integration.bayut_default_team_id", str(rec.default_team_id.id or ""))
                if "default_user_id" in vals:
                    params.set_param("bayut_lead_integration.bayut_default_user_id", str(rec.default_user_id.id or ""))
                if "sync_interval" in vals:
                    interval = max(int(rec.sync_interval or 10), 1)
                    params.set_param("bayut_lead_integration.bayut_sync_interval", str(interval))
                    cron = self.env.ref("bayut_lead_integration.ir_cron_bayut_sync_leads", raise_if_not_found=False)
                    if cron:
                        cron.sudo().write({"interval_number": interval, "interval_type": "minutes"})
        return res

    @api.model
    def _get_config_settings(self):
        """Fetch Bayut Leads & Listing API settings from ir.config_parameter / connector."""
        params = self.env["ir.config_parameter"].sudo()
        connector = self._get_connector()

        api_url = (
            params.get_param("bayut_lead_integration.bayut_api_url")
            or connector.api_url
            or DEFAULT_LEADS_API_URL
        ).strip()
        if any(host in api_url for host in PLACEHOLDER_LEADS_HOSTS):
            api_url = DEFAULT_LEADS_API_URL
        api_key = (
            params.get_param("bayut_lead_integration.bayut_api_key")
            or connector.api_key
            or ""
        ).strip()

        listing_api_url = (
            params.get_param("bayut_lead_integration.bayut_listing_api_url")
            or connector.listing_api_url
            or DEFAULT_LISTING_API_URL
        ).strip()
        if listing_api_url in OLD_LISTING_API_URLS:
            listing_api_url = DEFAULT_LISTING_API_URL
        listing_api_key = (
            params.get_param("bayut_lead_integration.bayut_listing_api_key")
            or connector.listing_api_key
            or api_key
            or ""
        ).strip()

        team_id_raw = params.get_param("bayut_lead_integration.bayut_default_team_id")
        user_id_raw = params.get_param("bayut_lead_integration.bayut_default_user_id")
        interval_raw = params.get_param("bayut_lead_integration.bayut_sync_interval", "10")

        team_id = (
            int(team_id_raw)
            if team_id_raw and str(team_id_raw).isdigit()
            else (connector.default_team_id.id if connector.default_team_id else False)
        )
        user_id = (
            int(user_id_raw)
            if user_id_raw and str(user_id_raw).isdigit()
            else (connector.default_user_id.id if connector.default_user_id else False)
        )
        try:
            sync_interval = max(int(interval_raw), 1)
        except (ValueError, TypeError):
            sync_interval = 10

        # Company for new leads: the setting, else the sales team's company
        company_raw = params.get_param("bayut_lead_integration.bayut_company_id")
        company_id = int(company_raw) if company_raw and str(company_raw).isdigit() else False
        if not company_id and team_id:
            company_id = self.env["crm.team"].sudo().browse(team_id).company_id.id or False

        return {
            "api_url": api_url,
            "api_key": api_key,
            "listing_api_url": listing_api_url,
            "listing_api_key": listing_api_key,
            "team_id": team_id,
            "user_id": user_id,
            "company_id": company_id,
            "sync_interval": sync_interval,
        }

    @api.model
    def _bayut_move_leads_to_company(self, company):
        """Move every Bayut lead (active or not) that sits in another company to `company`."""
        leads = self.env["crm.lead"].sudo().with_context(active_test=False).search([
            ("bayut_lead_id", "!=", False),
            "|", ("company_id", "=", False), ("company_id", "!=", company.id),
        ])
        # A sales team of the other company is not allowed on the moved lead
        wrong_team = leads.filtered(lambda l: l.team_id.company_id and l.team_id.company_id != company)
        if wrong_team:
            wrong_team.write({"team_id": False})
        if leads:
            leads.write({"company_id": company.id})
        return len(leads)

    # =========================================================================
    # 1. ISOLATED BAYUT LEAD PAYLOAD PARSER
    # =========================================================================
    # =========================================================================
    # HTTP helper: Bearer auth, rate-limit retry, honest result
    # =========================================================================
    @api.model
    def _bayut_request(self, method, url, token, params=None, json_body=None, timeout=30):
        """Call the Bayut Profolio API.

        Returns (ok, status_code, body) where ok is True only for a 2xx response.
        On HTTP 429 waits `retry_after` seconds (capped) and retries. Never raises.
        """
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
            try:
                resp = requests.request(method, url, headers=headers, params=params,
                                        json=json_body, timeout=timeout)
            except requests.exceptions.RequestException as exc:
                return False, 0, {"message": str(exc)}
            try:
                body = resp.json() if resp.content else {}
            except ValueError:
                body = {"message": resp.text[:500]}
            if resp.status_code == 429 and attempt < RATE_LIMIT_MAX_RETRIES:
                wait = body.get("retry_after") if isinstance(body, dict) else None
                try:
                    wait = min(max(int(wait or 2 ** (attempt + 1)), 1), RATE_LIMIT_MAX_WAIT)
                except (TypeError, ValueError):
                    wait = 2 ** (attempt + 1)
                _logger.info("Bayut rate limit hit on %s, retrying in %ss", url, wait)
                time.sleep(wait)
                continue
            return 200 <= resp.status_code < 300, resp.status_code, body
        return False, 429, body

    @staticmethod
    def _bayut_error_text(status, body):
        """Short human-readable error from a Bayut error response (incl. 422 field errors)."""
        if not isinstance(body, dict):
            return f"HTTP {status}: {str(body)[:300]}"
        msg = body.get("message") or body.get("error") or ""
        errors = body.get("errors")
        if isinstance(errors, dict):
            details = "; ".join(f"{k}: {', '.join(map(str, v)) if isinstance(v, list) else v}"
                                for k, v in errors.items())
            msg = f"{msg} ({details})" if msg else details
        return f"HTTP {status}: {msg or 'no error message'}"[:1000]

    @staticmethod
    def _str(value):
        return "" if value is None or value is False else str(value).strip()

    @staticmethod
    def _format_phone(value):
        """Bayut sends numbers without '+' (e.g. 971551234567)."""
        digits = re.sub(r"\D", "", str(value or ""))
        return f"+{digits}" if len(digits) >= 10 else digits

    @staticmethod
    def _format_timestamp(value):
        """Accept epoch seconds (call payload) or ISO strings (WhatsApp payload)."""
        if value in (None, False, ""):
            return ""
        if isinstance(value, (int, float)) or str(value).isdigit():
            try:
                return datetime.fromtimestamp(int(float(value)), tz=timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                )
            except (ValueError, OverflowError, OSError):
                return str(value)
        return str(value)

    @api.model
    def _parse_lead(self, raw_lead, portal=None):
        """Normalize one Bayut / dubizzle lead into a flat dict used by Odoo CRM.

        Supported formats (Bayut / dubizzle Push API documentation):
          * Call lead (Bayut):        id, agent{name,phone,email}, call_details{...},
                                      enquirer{phone_number}, portal
          * WhatsApp lead (Bayut):    id, agent{url,id,name,email,phone_number}?,
                                      listing{url,reference}?, message, received_at,
                                      enquirer{name,contact_link,phone_number,intent?}, wam_id
          * WhatsApp lead (dubizzle): id, enquirer{name,phone_number,contact_link},
                                      listing{url,reference}, received_at
          * Legacy flat format (client_name / email / phone / property_ref ...).
          * Pull API (GET /v1/leads): {lead{id,source,channel,date_time}, inquirer_details,
                                      agent_details, listing_details, call_details?} -> _parse_pull_lead
        """
        if not isinstance(raw_lead, dict):
            return {}
        if isinstance(raw_lead.get("lead"), dict):
            return self._parse_pull_lead(raw_lead)
        s = self._str

        def _sub(key):
            val = raw_lead.get(key)
            return val if isinstance(val, dict) else {}

        enquirer = _sub("enquirer")
        agent = _sub("agent")
        listing = _sub("listing")
        call = _sub("call_details")

        raw_id = raw_lead.get("id") or raw_lead.get("lead_id") or raw_lead.get("uid")
        contact_link = s(enquirer.get("contact_link"))

        portal = s(raw_lead.get("portal") or portal).lower()
        if not portal:
            portal = "dubizzle" if "dubizzle" in contact_link.lower() else "bayut"

        if call:
            lead_type = "call"
        elif "wam_id" in raw_lead or "whatsapp" in contact_link.lower():
            lead_type = "whatsapp"
        else:
            lead_type = s(
                raw_lead.get("type") or raw_lead.get("lead_type") or raw_lead.get("channel") or "email"
            ).lower()

        phone = (
            enquirer.get("phone_number")
            or raw_lead.get("phone")
            or raw_lead.get("client_phone")
            or raw_lead.get("mobile")
            or raw_lead.get("sender_phone")
        )
        property_ref = s(
            listing.get("reference")
            or raw_lead.get("property_ref")
            or raw_lead.get("property_reference")
            or raw_lead.get("reference")
            or raw_lead.get("listing_reference")
        )

        call_info = {}
        if call:
            call_info = {
                "status": s(call.get("call_status")),
                "pickup": self._format_timestamp(call.get("pickup_timestamp")),
                "duration": call.get("call_duration"),
                "total_duration": call.get("call_total_duration"),
                "proxy_number": s(call.get("proxy_number")),
            }

        return {
            "bayut_lead_id": self._normalize_lead_id(raw_id),
            "portal": portal,
            "lead_type": lead_type,
            "client_name": s(
                enquirer.get("name")
                or raw_lead.get("client_name")
                or raw_lead.get("name")
                or raw_lead.get("sender_name")
            ),
            "email": s(
                enquirer.get("email")
                or raw_lead.get("email")
                or raw_lead.get("client_email")
                or raw_lead.get("sender_email")
            ),
            "phone": self._format_phone(phone) if phone else "",
            "message": s(raw_lead.get("message") or raw_lead.get("body") or raw_lead.get("comments")),
            "property_ref": property_ref or "N/A",
            "listing_url": s(listing.get("url")),
            "contact_link": contact_link,
            "intent": s(enquirer.get("intent")),
            "agent_name": s(agent.get("name")),
            "agent_email": s(agent.get("email")),
            "agent_phone": s(agent.get("phone_number") or agent.get("phone")),
            "call_info": call_info,
            "created_at": self._format_timestamp(
                raw_lead.get("received_at")
                or call.get("pickup_timestamp")
                or raw_lead.get("created_at")
                or raw_lead.get("timestamp")
            ),
        }

    @staticmethod
    def _normalize_lead_id(raw_id):
        """Pull API ids are '<channel>|<id>' (e.g. 'phone|b320a3db-...'), push ids are the bare id.
        Store the bare id so a lead received both ways is only created once."""
        raw_id = "" if raw_id is None else str(raw_id).strip()
        return raw_id.split("|", 1)[1].strip() if "|" in raw_id else raw_id

    @api.model
    def _parse_pull_lead(self, item):
        """Normalize one record of GET /v1/leads (phone or WhatsApp)."""
        s = self._str

        def _sub(obj, key):
            val = obj.get(key) if isinstance(obj, dict) else None
            return val if isinstance(val, dict) else {}

        lead = _sub(item, "lead")
        inquirer = _sub(item, "inquirer_details")
        agent = _sub(item, "agent_details")
        listing = _sub(item, "listing_details")
        call = _sub(item, "call_details")
        callback = _sub(call, "callback")

        channel = s(lead.get("channel")).lower()
        call_info = {}
        if call:
            call_info = {
                "status": s(call.get("status")),
                "pickup": s(call.get("pickup_time") or call.get("time")),
                "duration": s(call.get("connected_duration")) or None,
                "total_duration": s(call.get("total_duration")) or None,
                "proxy_number": s(call.get("proxy_number")),
                "recording_url": s(call.get("recording_url")),
                "callback": (
                    f"{s(callback.get('status'))} at {s(callback.get('date_time'))}, "
                    f"{callback.get('duration')}s talk"
                ) if callback else "",
                "callback_recording_url": s(callback.get("recording_url")),
            }
        phone = inquirer.get("cell") or inquirer.get("phone")
        return {
            "bayut_lead_id": self._normalize_lead_id(lead.get("id")),
            "portal": s(lead.get("source") or "bayut").lower(),
            "lead_type": "call" if channel == "phone" else (channel or "email"),
            "client_name": s(inquirer.get("name")),
            "email": s(inquirer.get("email")),
            "phone": self._format_phone(phone) if phone else "",
            "message": s(inquirer.get("message")),
            "property_ref": s(listing.get("reference")) or "N/A",
            "listing_url": "",
            "bayut_listing_external_id": s(listing.get("id")),
            "contact_link": "",
            "intent": "",
            "enquirer_type": s(inquirer.get("enquirer_type")),
            "agent_name": s(agent.get("name")),
            "agent_email": s(agent.get("email")),
            "agent_phone": s(agent.get("phone")),
            "call_info": call_info,
            "created_at": s(lead.get("date_time")),
        }

    @api.model
    def _find_agent_user(self, agent_email):
        """Map the portal agent (by email) to an internal Odoo user."""
        if not agent_email:
            return self.env["res.users"]
        return self.env["res.users"].sudo().search(
            [("share", "=", False), "|", ("login", "=ilike", agent_email), ("email", "=ilike", agent_email)],
            limit=1,
        )

    @api.model
    def _build_lead_description(self, parsed):
        lines = []
        if parsed.get("message"):
            lines += [parsed["message"], ""]
        lines.append(_("Source: %(portal)s %(type)s lead",
                       portal=parsed["portal"].capitalize(), type=parsed["lead_type"]))
        if parsed.get("created_at"):
            lines.append(_("Received at: %s", parsed["created_at"]))
        if parsed.get("intent"):
            lines.append(_("Enquirer intent: %s", parsed["intent"]))
        if parsed.get("enquirer_type"):
            lines.append(_("Enquirer type: %s", parsed["enquirer_type"]))
        if parsed.get("listing_url"):
            lines.append(_("Listing: %s", parsed["listing_url"]))
        if parsed.get("contact_link"):
            lines.append(_("Contact link: %s", parsed["contact_link"]))
        agent_bits = [v for v in (parsed.get("agent_name"), parsed.get("agent_email"), parsed.get("agent_phone")) if v]
        if agent_bits:
            lines.append(_("Portal agent: %s", " / ".join(agent_bits)))
        call = parsed.get("call_info") or {}
        if call:
            lines.append(_(
                "Call: status=%(status)s, picked up=%(pickup)s, talk time=%(dur)ss, total=%(total)ss, proxy=%(proxy)s",
                status=call.get("status") or "-",
                pickup=call.get("pickup") or "-",
                dur=call.get("duration") if call.get("duration") is not None else "-",
                total=call.get("total_duration") if call.get("total_duration") is not None else "-",
                proxy=call.get("proxy_number") or "-",
            ))
            if call.get("recording_url"):
                lines.append(_("Call recording: %s", call["recording_url"]))
            if call.get("callback"):
                lines.append(_("Callback: %s", call["callback"]))
            if call.get("callback_recording_url"):
                lines.append(_("Callback recording: %s", call["callback_recording_url"]))
        if parsed["lead_type"] in INTENT_SIGNAL_TYPES:
            lines.append(INTENT_SIGNAL_NOTE)
        return "\n".join(lines)

    @api.model
    def _verify_push_signature(self, portal, raw_body, received_signature):
        """Bayut/dubizzle sign the body as md5(secret_key . body) (hex, lowercase).

        Returns (accepted: bool, note: str). If no secret is configured yet the lead is
        accepted (portals only issue the secret after registering the endpoint) but
        flagged as unverified in the sync log.
        """
        header, param_key = PUSH_PORTALS.get(portal, PUSH_PORTALS["bayut"])
        secret = (self.env["ir.config_parameter"].sudo().get_param(param_key) or "").strip()
        if not secret:
            return True, _("UNVERIFIED: no %s push secret configured yet.", portal.capitalize())
        if isinstance(raw_body, str):
            raw_body = raw_body.encode("utf-8")
        expected = hashlib.md5(secret.encode("utf-8") + raw_body).hexdigest()
        if received_signature and hmac.compare_digest(expected, received_signature.strip().lower()):
            return True, ""
        return False, _("Invalid or missing %s header.", header)

    # =========================================================================
    # 2. ISOLATED BAYUT LISTING PAYLOAD BUILDER & PUSH ENGINE
    # =========================================================================
    @api.model
    def _prepare_listing_payload(self, listing, action="publish"):
        """Build the JSON payload for creating/updating/unpublishing a property
        listing on Bayut Profolio via the Listing API.

        TODO: Adjust field names in this single method if Bayut's Listing API
        schema uses different property keys.
        """
        data = listing._to_bayut_dict()
        data["action"] = action
        data["status"] = "inactive" if action == "unpublish" else "active"
        return data

    @api.model
    def push_listings_to_bayut(self, listings=None, action="publish"):
        """Push one or more `bayut.listing` records to the Bayut Listing API
        using Bearer token authentication (`listing_api_key`), and update feed state.
        Never crashes on network errors; logs every operation to `bayut.sync.log`.
        """
        # Publishing from Odoo (POST /v1/properties + /products/attach) is not connected yet.
        # Never change the listing state or claim success here: the real status is read
        # from Bayut by _sync_listings_from_bayut().
        msg = _(
            "Publishing from Odoo to Bayut is not connected yet. Create, edit or remove the listing "
            "in Profolio; Odoo reads the live status from Bayut every 15 minutes (or click Refresh from Bayut)."
        )
        return {"status": "error", "listings_synced": 0, "message": msg}

    # =========================================================================
    # READ THE TRUTH FROM BAYUT: GET /v1/properties -> Odoo listings
    # =========================================================================
    @staticmethod
    def _bayut_text(value):
        """Bayut returns translatable fields as {"en": ..., "ar": ...}."""
        if isinstance(value, dict):
            return (value.get("en") or value.get("ar") or "").strip()
        return ("" if value is None else str(value)).strip()

    @api.model
    def _bayut_portal_states(self, prop):
        """-> ({'bayut': 'active', 'dubizzle': 'active'}, 'published'|'unpublished')

        Scope is Bayut only for now: "published" means live on the Bayut portal.
        Other portals (dubizzle) are reported for information only."""
        states = {}
        for portal in prop.get("portals") or []:
            if isinstance(portal, dict) and portal.get("name"):
                states[portal["name"]] = portal.get("state") or ""
        live = states.get(ACTIVE_PORTAL) == "active"
        return states, ("published" if live else "unpublished")

    @api.model
    def _bayut_status_vals(self, prop, listing=None):
        """Odoo listing values that mirror Bayut's view of a property (status, permit, location).

        Permit number and location are only filled in when the Odoo listing has none: what the
        user typed in Odoo is never overwritten by a refresh (it is what the next update sends)."""
        portals, state = self._bayut_portal_states(prop)
        portal_state = portals.get(ACTIVE_PORTAL)
        bayut_comment = (prop.get("comment") or "").strip()    # Bayut's rejection reason, e.g. "Invalid Permit Number"
        if state != "published" and portal_state:
            # inactive = Bayut refused / deactivated it (duplicate or invalid permit, mismatch...);
            # anything else (draft, unpublished without a reason) = still under Bayut review
            state = "inactive" if (portal_state == "inactive" or bayut_comment) else "pending"
        portal_text = ", ".join(f"{k}: {v}" for k, v in sorted(portals.items())) or "-"
        permit = prop.get("permit") or {}
        vals = {
            "bayut_external_id": str(prop.get("id")),
            "state": state,
            "active": True,
            "bayut_portal_status": portal_text,
            "permit_status": " - ".join(
                x for x in (bayut_comment, permit.get("status"), permit.get("comment")) if x) or False,
            "verification_state": prop.get("verification_state") or False,
            "last_bayut_sync": fields.Datetime.now(),
            "last_sync_message": _("Bayut status: %(portals)s. Permit: %(permit)s",
                                   portals=portal_text,
                                   permit=" - ".join(x for x in (permit.get("status"), permit.get("comment")) if x) or "-"),
        }
        if (permit.get("number") or "").strip() and not (listing and listing.permit_number):
            vals["permit_number"] = permit["number"].strip()
        # Details Odoo does not edit but must send back on update (Bayut PUT replaces everything)
        rental = prop.get("rental_details") if isinstance(prop.get("rental_details"), dict) else {}
        vals["bayut_extra_json"] = json.dumps({
            "amenities": [{"id": str(a.get("id")), "value": str(a.get("value") if a.get("value") is not None else "true")}
                          for a in (prop.get("amenities") or []) if isinstance(a, dict) and a.get("id")],
            "rental_details": {k: rental.get(k) for k in (
                "occupancy_status", "rent_frequency", "minimum_contract_period", "vacating_notice_period",
                "maintenance_fee", "maintenance_fee_paid_by") if rental.get(k) not in (None, "", 0)},
            "furnishing_status": prop.get("furnishing_status"),
        })
        location = self.env["bayut.location"]._upsert_from_bayut(prop.get("location") or {})
        if location and not (listing and listing.bayut_location):
            vals["bayut_location"] = location.id
            vals["bayut_location_id"] = str(location.bayut_id)
        return vals

    @api.model
    def _bayut_import_images(self, listing, prop):
        """Keep Bayut-hosted photos on listings that have none in Odoo, so an update from
        Odoo (which must resend every field) never wipes the photos on Bayut."""
        if listing.image_ids or listing.image_1920:
            return
        vals = []
        for seq, img in enumerate(prop.get("images") or []):
            url = img.get("url") or img.get("path") if isinstance(img, dict) else None
            if url:
                vals.append((0, 0, {"sequence": seq if not img.get("is_main") else -1,
                                    "name": img.get("title") or False, "remote_url": url}))
        if vals:
            listing.with_context(skip_bayut_auto_sync=True).write({"image_ids": vals})

    @api.model
    def _odoo_vals_from_bayut(self, prop):
        """Listing values for a Bayut property that has no Odoo listing yet."""
        t = self._bayut_text
        purpose = t(prop.get("purpose")).lower()
        category = prop.get("category") or {}
        cat_title = t(category.get("title")).lower()
        type_map = [("penthouse", "Penthouse"), ("villa", "Villa"), ("townhouse", "Townhouse"),
                    ("hotel", "Hotel Apartment"), ("office", "Office"), ("shop", "Shop"),
                    ("warehouse", "Warehouse")]
        prop_type = next((v for k, v in type_map if k in cat_title), "Apartment")
        beds = prop.get("bedrooms")
        beds = 0 if beds in (None, -1) else min(int(beds), 7)
        location = prop.get("location") or {}
        crumbs = (location.get("breadcrumb") or {}).get("en") or []
        rental = prop.get("rental_details") or {}
        furnishing = prop.get("furnishing_status")
        return {
            "name": t(prop.get("title"))[:255] or prop.get("reference"),
            "reference_number": prop.get("reference"),
            "purpose": "for-sale" if "sale" in purpose or "buy" in purpose else "for-rent",
            "category": "commercial" if (category.get("parent_title") or "").lower() == "commercial" else "residential",
            "property_type": prop_type,
            "price": float(prop.get("price") or 0.0),
            "rent_frequency": rental.get("rent_frequency") or "yearly",
            "bedrooms": str(beds),
            "bathrooms": int(prop.get("bathrooms") or 0),
            "size_sqft": float(prop.get("area") or 0.0),
            "furnished": "furnished" if furnishing == "furnished" else "unfurnished",
            "completion_status": "off_plan" if prop.get("completion_status") == "off_plan" else "completed",
            "city": crumbs[1] if len(crumbs) > 1 else "Dubai",
            "community": crumbs[2] if len(crumbs) > 2 else "",
            "sub_community": crumbs[3] if len(crumbs) > 3 else "",
            "building_name": t(location.get("title")),
            "bayut_location_id": str(location.get("id") or ""),
            "description_en": t(prop.get("description")),
            "title_ar": ((prop.get("title") or {}).get("ar") or "") if isinstance(prop.get("title"), dict) else "",
            "description_ar": ((prop.get("description") or {}).get("ar") or "")
            if isinstance(prop.get("description"), dict) else "",
        }

    @api.model
    def _sync_listings_from_bayut(self):
        """Mirror the real Bayut status into Odoo (read-only towards Bayut).

        * every Bayut property is linked to an Odoo listing (by Bayut ID, permit number or
          reference) or created as a new Odoo listing;
        * state = published when live on at least one portal, else unpublished;
        * Odoo listings marked published that are NOT on Bayut go back to draft.
        """
        connector = self._get_connector()
        cfg = self._get_config_settings()
        token = cfg["listing_api_key"] or cfg["api_key"]
        Listing = self.env["bayut.listing"].sudo().with_context(skip_bayut_auto_sync=True, active_test=False)
        LogModel = self.env["bayut.sync.log"].sudo()
        now = fields.Datetime.now()

        if not token:
            msg = _("Listing status sync skipped: no Bayut API token configured in Settings.")
            LogModel.create({"connector_id": connector.id, "sync_datetime": now, "sync_type": "listings",
                             "status": "error", "message": msg})
            return {"status": "error", "listings_synced": 0, "message": msg}

        props, page = [], 1
        while True:
            ok, status, body = self._bayut_request(
                "GET", f"{BAYUT_API_BASE}/properties", token, params={"page": page, "per_page": 100}
            )
            if not ok:
                msg = _("Could not read listings from Bayut: %s", self._bayut_error_text(status, body))
                LogModel.create({"connector_id": connector.id, "sync_datetime": now, "sync_type": "listings",
                                 "status": "error", "message": msg})
                return {"status": "error", "listings_synced": 0, "message": msg}
            data = body.get("data") or []
            props.extend(data)
            if not (body.get("links") or {}).get("next") or not data:
                break
            page += 1

        created = linked = changed = 0
        seen_ids = set()
        for prop in props:
            bayut_id = str(prop.get("id") or "")
            if not bayut_id:
                continue
            seen_ids.add(bayut_id)
            permit = ((prop.get("permit") or {}).get("number") or "").strip()

            listing = Listing.search([("bayut_external_id", "=", bayut_id)], limit=1)
            if not listing and permit:
                listing = Listing.search([("permit_number", "=", permit), ("bayut_external_id", "=", False)], limit=1)
            if not listing and prop.get("reference"):
                listing = Listing.search([("reference_number", "=", prop["reference"])], limit=1)

            sync_vals = self._bayut_status_vals(prop, listing or None)
            if not listing:
                listing = Listing.create({**self._odoo_vals_from_bayut(prop), **sync_vals})
                self._bayut_import_images(listing, prop)
                created += 1
                continue
            if not listing.bayut_external_id:
                linked += 1
            if listing.state != sync_vals["state"] or listing.bayut_external_id != bayut_id:
                changed += 1
            listing.write(sync_vals)
            self._bayut_import_images(listing, prop)

        # Listings Odoo believed were live but that are not on Bayut
        stale = Listing.search([("state", "=", "published"), "|",
                                ("bayut_external_id", "=", False),
                                ("bayut_external_id", "not in", list(seen_ids) or ["-"])])
        if stale:
            stale.write({
                "state": "draft",
                "last_bayut_sync": now,
                "last_sync_message": _("Not found on Bayut: set back to Draft."),
            })
        # Attach Bayut leads that arrived before their listing existed in Odoo
        Lead = self.env["crm.lead"].sudo()
        for listing in Listing.search([("bayut_external_id", "in", list(seen_ids) or ["-"])]):
            orphan_leads = Lead.search([("bayut_listing_id", "=", False),
                                        ("bayut_property_ref", "=", listing.reference_number)])
            if orphan_leads:
                orphan_leads.write({"bayut_listing_id": listing.id})

        connector.sudo().with_context(skip_param_sync=True).write({"last_listing_sync": now})

        msg = _(
            "Bayut status sync: %(total)d listing(s) on Bayut, %(created)d added to Odoo, %(linked)d linked, "
            "%(changed)d status update(s), %(stale)d Odoo listing(s) not on Bayut set back to Draft.",
            total=len(props), created=created, linked=linked, changed=changed, stale=len(stale),
        )
        if created or linked or changed or stale:
            LogModel.create({"connector_id": connector.id, "sync_datetime": now, "sync_type": "listings",
                             "status": "success", "listings_synced": len(props), "message": msg})
        return {"status": "success", "listings_synced": len(props), "message": msg}

    @api.model
    def cron_sync_listings(self):
        """Scheduled job: read the real listing status from Bayut (no pushes)."""
        try:
            return self._sync_listings_from_bayut()
        except Exception as exc:
            _logger.exception("Error in cron_sync_listings")
            return {"status": "error", "listings_synced": 0, "message": str(exc)}

    @api.model
    def _auto_sync_from_odoo_properties(self):
        """Optional helper: if `property.detail` (eg_property_management) is installed in the
        database, sync any units linked via `source_property_ref` so price/vacancy updates flow automatically."""
        if "property.detail" not in self.env:
            return 0
        PropModel = self.env["property.detail"].sudo()
        ListingModel = self.env["bayut.listing"].sudo()
        linked_listings = ListingModel.search([("source_property_ref", "!=", False)])
        updated = 0
        for listing in linked_listings:
            prop = PropModel.browse(listing.source_property_ref).exists()
            if not prop:
                continue
            price_val = (
                float(getattr(prop, "rent_amount", 0.0) or getattr(prop, "final_price", 0.0) or 0.0)
                if getattr(prop, "property_for", "rent") == "rent"
                else float(getattr(prop, "sale_amount", 0.0) or getattr(prop, "final_price", 0.0) or 0.0)
            )
            vals = {}
            if price_val > 0 and price_val != listing.price:
                vals["price"] = price_val
            if getattr(prop, "state", "") in ("on_rent", "rent", "sold") and listing.state == "published":
                vals["state"] = "unpublished"
            if vals:
                listing.with_context(skip_bayut_auto_sync=True).write(vals)
                updated += 1
        return updated

    def action_import_from_odoo_properties(self):
        """One-click import of existing `property.detail` units into standalone `bayut.listing` records."""
        if "property.detail" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Standalone Mode"),
                    "message": _("No external property.detail table detected. Create listings directly in Bayut Listings."),
                    "type": "info",
                    "sticky": False,
                },
            }

        PropModel = self.env["property.detail"].sudo()
        ListingModel = self.env["bayut.listing"].sudo()
        all_props = PropModel.search([])
        created_count = 0
        updated_count = 0

        for prop in all_props:
            ref_code = (getattr(prop, "code", False) or prop.name or f"UNIT-{prop.id}").strip()
            existing = ListingModel.search(
                ["|", ("source_property_ref", "=", prop.id), ("reference_number", "=", ref_code)],
                limit=1,
            )
            is_rent = getattr(prop, "property_for", "rent") != "sale"
            price_val = (
                float(getattr(prop, "rent_amount", 0.0) or getattr(prop, "final_price", 0.0) or 0.0)
                if is_rent
                else float(getattr(prop, "sale_amount", 0.0) or getattr(prop, "final_price", 0.0) or 0.0)
            )
            beds = int(getattr(prop, "bedrooms", 0) or getattr(prop, "no_of_bhk", 0) or 0)
            beds_str = str(min(beds, 7))

            res_type_str = str(getattr(prop, "residential_type", "") or "").lower()
            if "villa" in res_type_str:
                p_type = "Villa"
            elif "townhouse" in res_type_str or "raw house" in res_type_str:
                p_type = "Townhouse"
            elif "pent" in res_type_str:
                p_type = "Penthouse"
            elif "office" in res_type_str or getattr(prop, "property_type", "") == "commercial":
                p_type = "Office"
            else:
                p_type = "Apartment"

            furn_map = {
                "unfurnished": "unfurnished",
                "semi_furnished": "partly_furnished",
                "fully_furnished": "furnished",
            }
            furn_val = furn_map.get(getattr(prop, "furnishing", "unfurnished"), "unfurnished")

            proj_name = prop.project_id.name if hasattr(prop, "project_id") and prop.project_id else ""
            sub_proj_name = prop.sub_project_id.name if hasattr(prop, "sub_project_id") and prop.sub_project_id else ""

            vals = {
                "name": f"{prop.name} - {proj_name}" if proj_name else prop.name,
                "reference_number": ref_code,
                "source_property_ref": prop.id,
                "purpose": "for-rent" if is_rent else "for-sale",
                "category": "commercial" if getattr(prop, "property_type", "") == "commercial" else "residential",
                "property_type": p_type,
                "price": price_val,
                "bedrooms": beds_str,
                "bathrooms": int(getattr(prop, "bathrooms", 1) or 1),
                "size_sqft": float(getattr(prop, "total_area", 0.0) or getattr(prop, "usable_area", 0.0) or 0.0),
                "parking_spaces": int(getattr(prop, "parking", 0) or 0),
                "furnished": furn_val,
                "city": getattr(prop, "city", False) or "Dubai",
                "community": proj_name or getattr(prop, "street", False) or "Dubai",
                "sub_community": sub_proj_name or getattr(prop, "street2", False) or "",
                "building_name": sub_proj_name or proj_name or prop.name,
                "description_en": getattr(prop, "website_short_description", False) or prop.name,
                "image_1920": getattr(prop, "image_1920", False),
            }
            if existing:
                existing.with_context(skip_bayut_auto_sync=True).write(vals)
                updated_count += 1
            else:
                # Always Draft: a listing is only "Published" once Bayut confirms it is live
                ListingModel.with_context(skip_bayut_auto_sync=True).create(vals)
                created_count += 1

        msg = _(
            "Imported %(created)d new listing(s) and updated %(updated)d existing listing(s) from Odoo Properties.",
            created=created_count,
            updated=updated_count,
        )
        self.env["bayut.sync.log"].sudo().create({
            "connector_id": self._get_connector().id,
            "sync_datetime": fields.Datetime.now(),
            "sync_type": "listings",
            "status": "success",
            "listings_synced": created_count + updated_count,
            "message": msg,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Properties Imported to Bayut Listings"),
                "message": msg,
                "type": "success",
                "sticky": False,
            },
        }

    # =========================================================================
    # DE-DUPLICATION & PARTNER / LEAD MATCHING HELPERS
    # =========================================================================
    @staticmethod
    def _normalize_phone(phone):
        """Return digits-only representation (last 9 digits for UAE/international matching)."""
        if not phone:
            return ""
        digits = re.sub(r"\D", "", str(phone))
        return digits[-9:] if len(digits) >= 9 else digits

    @api.model
    def _find_matching_partner(self, email, phone, client_name=None):
        """Try to match an existing res.partner by email or phone number."""
        Partner = self.env["res.partner"].sudo()
        if email:
            partner = Partner.search([("email", "=ilike", email)], limit=1)
            if partner:
                return partner

        norm_phone = self._normalize_phone(phone)
        if norm_phone:
            domain = (
                ["|", ("phone", "ilike", norm_phone), ("mobile", "ilike", norm_phone)]
                if "mobile" in Partner._fields
                else [("phone", "ilike", norm_phone)]
            )
            partner = Partner.search(domain, limit=1)
            if partner:
                return partner

        return Partner

    @api.model
    def _find_matching_existing_lead(self, email, phone, property_ref):
        """Find an existing active CRM lead with the same email or phone so we can
        reuse its partner or attach follow-up activity when it targets the same property."""
        Lead = self.env["crm.lead"].sudo()
        norm_phone = self._normalize_phone(phone)

        contact_clauses = []
        if email:
            contact_clauses.append(("email_from", "=ilike", email))
        if norm_phone:
            contact_clauses.append(("phone", "ilike", norm_phone))

        if not contact_clauses:
            return Lead, Lead

        if len(contact_clauses) == 2:
            contact_domain = ["|"] + contact_clauses
        else:
            contact_domain = contact_clauses

        existing_leads = Lead.search(contact_domain, order="id desc", limit=10)
        same_property_lead = Lead
        if property_ref and property_ref != "N/A":
            same_property_lead = existing_leads.filtered(
                lambda l: (l.bayut_property_ref or "").strip().lower() == property_ref.lower()
            )[:1]
        return existing_leads[:1], same_property_lead

    @api.model
    def _find_matching_bayut_listing(self, property_ref):
        """Match a standalone `bayut.listing` record by `reference_number`."""
        if not property_ref or property_ref == "N/A":
            return self.env["bayut.listing"]
        return self.env["bayut.listing"].sudo().search(
            [("reference_number", "=ilike", property_ref)], limit=1
        )

    @api.model
    def _find_matching_property_record(self, property_ref):
        """If eg_property_management (`property.detail`) is installed, try to match the unit."""
        if not property_ref or property_ref == "N/A" or "property.detail" not in self.env:
            return False
        Prop = self.env["property.detail"].sudo()
        domain = ["|", ("code", "=ilike", property_ref), ("name", "=ilike", property_ref)]
        return Prop.search(domain, limit=1)

    # =========================================================================
    # CONNECTION TEST & LEADS SYNC EXECUTION
    # =========================================================================
    @api.model
    def test_api_connection(self):
        """Verify the configured Bayut API Key & endpoints and log the test."""
        connector = self._get_connector()
        cfg = self._get_config_settings()
        LogModel = self.env["bayut.sync.log"].sudo()
        token = cfg["listing_api_key"] or cfg["api_key"]

        if not token:
            msg = _("Please enter your Bayut API Key before testing the connection.")
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": fields.Datetime.now(),
                "sync_type": "test",
                "status": "error",
                "message": msg,
            })
            return {"success": False, "message": msg}

        # Real check: an authenticated call that every valid Profolio token can make
        ok, status, body = self._bayut_request(
            "GET", f"{BAYUT_API_BASE}/users", token, params={"per_page": 50}
        )
        if ok:
            users = body.get("data") or [] if isinstance(body, dict) else []
            params = self.env["ir.config_parameter"].sudo()
            if len(users) == 1 and not params.get_param("bayut_lead_integration.bayut_default_bayut_user_id"):
                params.set_param("bayut_lead_integration.bayut_default_bayut_user_id", str(users[0].get("id")))
            names = ", ".join(
                f"{(u.get('name') or {}).get('en') or u.get('id')} (ID {u.get('id')})" for u in users[:5]
            )
            msg = _(
                "Connected to Bayut Profolio (HTTP %(status)s). Bayut users in your agency: %(names)s. "
                "Leads arrive by webhook at %(hook)s and are pulled as backup from %(pull)s.",
                status=status, names=names or _("none returned"),
                hook=connector.webhook_url, pull=cfg["api_url"],
            )
        else:
            msg = _("Bayut Profolio connection FAILED: %s. Check the API token in Settings.",
                    self._bayut_error_text(status, body))
        LogModel.create({
            "connector_id": connector.id,
            "sync_datetime": fields.Datetime.now(),
            "sync_type": "test",
            "status": "success" if ok else "error",
            "message": msg,
        })
        return {"success": ok, "message": msg}

    @api.model
    def _process_incoming_leads_payload(self, payload, source="cron", since_str="", portal=None, note="",
                                        write_log=True):
        """Process a parsed JSON payload containing Bayut leads and create `crm.lead` records.
        With write_log=False no sync log is written (the caller aggregates the counts)."""
        connector = self._get_connector()
        cfg = self._get_config_settings()
        sync_start = fields.Datetime.now()
        LogModel = self.env["bayut.sync.log"].sudo()

        if isinstance(payload, dict):
            raw_leads = payload.get("leads", payload.get("data", []))
            if isinstance(raw_leads, dict):
                raw_leads = [raw_leads]
            elif not raw_leads and any(
                k in payload for k in ("id", "lead_id", "client_name", "property_ref", "enquirer")
            ):
                raw_leads = [payload]
        elif isinstance(payload, list):
            raw_leads = payload
        else:
            raw_leads = []

        if not isinstance(raw_leads, list):
            raw_leads = []

        leads_created = 0
        leads_skipped = 0
        leads_attached = 0
        leads_failed = 0
        LeadModel = self.env["crm.lead"].sudo()

        for raw_item in raw_leads:
            try:
                parsed = self._parse_lead(raw_item, portal=portal)
                if not parsed:
                    continue

                bayut_lead_id = parsed["bayut_lead_id"]
                lead_type = parsed["lead_type"]
                property_ref = parsed["property_ref"]
                client_name = parsed["client_name"]
                email = parsed["email"]
                phone = parsed["phone"]
                message = parsed["message"]
                created_at = parsed["created_at"]

                # 1. Primary De-duplication: skip if this Bayut id already created a lead
                #    or was already attached to one as extra activity (push + pull overlap)
                if bayut_lead_id:
                    existing_by_id = LeadModel.with_context(active_test=False).search(
                        ["|", ("bayut_lead_id", "=", bayut_lead_id),
                         ("bayut_activity_ids", "ilike", f"|{bayut_lead_id}|")], limit=1
                    )
                    if existing_by_id:
                        leads_skipped += 1
                        continue

                # 2. Partner & Existing Lead Matching by email or phone
                partner = self._find_matching_partner(email, phone, client_name=client_name)
                existing_contact_lead, same_property_lead = self._find_matching_existing_lead(
                    email, phone, property_ref
                )
                if not partner and existing_contact_lead and existing_contact_lead.partner_id:
                    partner = existing_contact_lead.partner_id

                if same_property_lead and same_property_lead.active:
                    if bayut_lead_id and not same_property_lead.bayut_lead_id:
                        same_property_lead.write({"bayut_lead_id": bayut_lead_id})
                    elif bayut_lead_id:
                        same_property_lead.write({
                            "bayut_activity_ids": f"{same_property_lead.bayut_activity_ids or '|'}{bayut_lead_id}|"
                        })
                    note_body = _(
                        "Additional Bayut activity received (%(type)s) for property %(ref)s: %(msg)s",
                        type=lead_type,
                        ref=property_ref,
                        msg=message or _("No message text"),
                    )
                    if lead_type in INTENT_SIGNAL_TYPES:
                        note_body = f"{note_body}\n{INTENT_SIGNAL_NOTE}"
                    same_property_lead.message_post(body=note_body)
                    leads_attached += 1
                    continue

                # 3. Build description, title and salesperson
                matched_listing = self._find_matching_bayut_listing(property_ref)
                agent_user = self._find_agent_user(parsed.get("agent_email"))
                if agent_user:
                    user_id = agent_user.id
                elif matched_listing and matched_listing.agent_user_id:
                    user_id = matched_listing.agent_user_id.id
                else:
                    user_id = cfg["user_id"] or False

                who = client_name or phone or email or _("Unknown enquirer")
                title_ref = property_ref if property_ref != "N/A" else who
                lead_vals = {
                    "name": f"[{parsed['portal'].capitalize()} {lead_type}] {title_ref}",
                    "contact_name": client_name or False,
                    "email_from": email or False,
                    "phone": phone or False,
                    "description": self._build_lead_description(parsed),
                    "team_id": cfg["team_id"] or False,
                    "user_id": user_id,
                    "bayut_lead_id": bayut_lead_id or False,
                    "bayut_lead_type": lead_type,
                    "bayut_property_ref": property_ref,
                    "bayut_listing_id": matched_listing.id if matched_listing else False,
                }

                if partner:
                    lead_vals["partner_id"] = partner.id

                if lead_type in INTENT_SIGNAL_TYPES:
                    lead_vals["priority"] = "0"

                matched_property = self._find_matching_property_record(property_ref)
                if matched_property and "property_id" in LeadModel._fields:
                    lead_vals["property_id"] = matched_property.id

                if cfg.get("company_id"):
                    lead_vals["company_id"] = cfg["company_id"]
                with self.env.cr.savepoint():
                    new_lead = LeadModel.create(lead_vals)
                if lead_type in INTENT_SIGNAL_TYPES:
                    new_lead.message_post(body=INTENT_SIGNAL_NOTE)

                leads_created += 1
            except Exception as item_exc:
                leads_failed += 1
                _logger.exception("Failed to import individual Bayut lead %s: %s", raw_item, item_exc)

        counts = {"created": leads_created, "attached": leads_attached,
                  "skipped": leads_skipped, "failed": leads_failed}
        if not write_log:
            return {"status": "error" if leads_failed else "success", "leads_created": leads_created,
                    "counts": counts, "message": ""}

        connector.sudo().with_context(skip_param_sync=True).write({"last_sync": sync_start})

        summary_msg = _(
            "Lead Sync (%(source)s) completed: %(created)d lead(s) created, "
            "%(attached)d attached to existing leads, %(skipped)d duplicate(s) skipped, %(failed)d failed.",
            source=f"{source.upper()} {portal.upper()}" if portal else source.upper(),
            created=leads_created,
            attached=leads_attached,
            skipped=leads_skipped,
            failed=leads_failed,
        )
        if note:
            summary_msg = f"{summary_msg} {note}"
        LogModel.create({
            "connector_id": connector.id,
            "sync_datetime": sync_start,
            "sync_type": "leads",
            "status": "error" if leads_failed else "success",
            "leads_created": leads_created,
            "message": summary_msg,
        })
        return {
            "status": "success",
            "leads_created": leads_created,
            "message": summary_msg,
        }

    @api.model
    def cron_sync_leads(self):
        """Backup pull of Bayut leads (GET /v1/leads) next to the real-time push webhook.

        Pulls phone + WhatsApp leads (is_lead=1) for the last PULL_LOOKBACK_DAYS days
        (PULL_INITIAL_DAYS on the very first run, to recover leads received before the webhook
        existed), page by page. Leads already received through the webhook are skipped by id.
        Writes ONE sync log: success only when every request returned 2xx. Never raises.
        """
        connector = self._get_connector()
        cfg = self._get_config_settings()
        params_store = self.env["ir.config_parameter"].sudo()
        sync_start = fields.Datetime.now()
        LogModel = self.env["bayut.sync.log"].sudo()

        if not cfg["api_key"]:
            msg = _("Bayut lead pull skipped: no Bayut API token configured in Settings.")
            LogModel.create({"connector_id": connector.id, "sync_datetime": sync_start,
                             "sync_type": "leads", "status": "error", "message": msg})
            return {"status": "error", "leads_created": 0, "message": msg}

        first_run = not params_store.get_param("bayut_lead_integration.leads_pull_done")
        days = PULL_INITIAL_DAYS if first_run else PULL_LOOKBACK_DAYS
        today = fields.Date.context_today(self)
        date_from = today - timedelta(days=days)
        totals = {"created": 0, "attached": 0, "skipped": 0, "failed": 0}
        fetched = 0
        errors = []

        for channel in PULL_CHANNELS:
            page = 1
            while True:
                query = {
                    "channel": channel,
                    "is_lead": 1,
                    "created_from": date_from.isoformat(),
                    "created_to": today.isoformat(),
                    "page": page,
                    "per_page": PULL_PER_PAGE,
                }
                if channel == "whatsapp":
                    query["target"] = "listing"
                ok, status, body = self._bayut_request("GET", cfg["api_url"], cfg["api_key"], params=query)
                if not ok:
                    errors.append(f"{channel} page {page}: {self._bayut_error_text(status, body)}")
                    break
                items = body.get("data") if isinstance(body, dict) else None
                if not items:
                    break
                fetched += len(items)
                res = self._process_incoming_leads_payload(
                    items, source="pull", write_log=False
                )
                for k, v in res.get("counts", {}).items():
                    totals[k] += v
                meta = body.get("meta") or {}
                if page * PULL_PER_PAGE >= int(meta.get("total") or 0) or len(items) < PULL_PER_PAGE:
                    break
                page += 1

        ok_run = not errors
        if ok_run:
            connector.sudo().with_context(skip_param_sync=True).write({"last_sync": sync_start})
            if first_run:
                params_store.set_param("bayut_lead_integration.leads_pull_done", "1")

        msg = _(
            "Lead pull (%(frm)s to %(to)s): %(fetched)d received from Bayut, %(created)d new lead(s) created, "
            "%(attached)d added to existing leads, %(skipped)d already in Odoo, %(failed)d failed.",
            frm=date_from.isoformat(), to=today.isoformat(), fetched=fetched, **totals,
        )
        if errors:
            msg = f"{msg} " + _("Errors: %s", " | ".join(errors))
        # Quiet runs (nothing new, no error) are not logged, to keep Sync Logs readable
        if errors or totals["created"] or totals["attached"] or totals["failed"] or first_run:
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": sync_start,
                "sync_type": "leads",
                "status": "success" if ok_run and not totals["failed"] else "error",
                "leads_created": totals["created"],
                "message": msg,
            })
        return {
            "status": "success" if ok_run else "error",
            "leads_created": totals["created"],
            "message": msg,
        }

    # =========================================================================
    # CONNECTOR FORM BUTTON ACTIONS
    # =========================================================================
    def action_test_connection(self):
        res = self.test_api_connection()
        notif_type = "success" if res.get("success") else "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Bayut Connection Status"),
                "message": res.get("message", ""),
                "type": notif_type,
                "sticky": False,
            },
        }

    def action_sync_now(self):
        """Manual trigger from the connector form view to sync leads."""
        res = self.cron_sync_leads()
        notif_type = "success" if res.get("status") == "success" else "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Bayut Lead Sync"),
                "message": res.get("message", ""),
                "type": notif_type,
                "sticky": False,
            },
        }

    def action_sync_listings_now(self):
        """Manual trigger from the connector form view to push all published listings."""
        res = self.cron_sync_listings()
        notif_type = "success" if res.get("status") == "success" else "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Bayut Listing Sync"),
                "message": res.get("message", ""),
                "type": notif_type,
                "sticky": False,
            },
        }

    def action_view_sync_logs(self):
        self.ensure_one()
        return {
            "name": _("Bayut Sync Logs"),
            "type": "ir.actions.act_window",
            "res_model": "bayut.sync.log",
            "view_mode": "list,form",
        }

    def action_view_listings(self):
        return {
            "name": _("Bayut Property Listings"),
            "type": "ir.actions.act_window",
            "res_model": "bayut.listing",
            "view_mode": "kanban,list,form",
        }

    def action_view_bayut_leads(self):
        return {
            "name": _("Bayut CRM Leads"),
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "domain": [("bayut_lead_id", "!=", False)],
        }
