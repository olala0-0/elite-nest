# -*- coding: utf-8 -*-
import logging
import re
from datetime import timedelta

import requests

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

INTENT_SIGNAL_TYPES = {"phone_view", "sms_click"}
INTENT_SIGNAL_NOTE = _(
    "Note: This is an intent signal (user viewed phone number or clicked SMS on Bayut), not a full lead."
)


class BayutConnector(models.Model):
    _name = "bayut.connector"
    _description = "Bayut Leads API Connector"
    _rec_name = "name"

    name = fields.Char(
        string="Connector Name",
        default="Bayut Leads Connector",
        required=True,
    )
    last_sync = fields.Datetime(
        string="Last Successful Sync",
        readonly=True,
        help="Timestamp of the last successful Bayut leads synchronization.",
    )
    log_ids = fields.One2many(
        comodel_name="bayut.sync.log",
        inverse_name="connector_id",
        string="Sync Logs",
        readonly=True,
    )
    log_count = fields.Integer(
        string="Sync Log Count",
        compute="_compute_log_count",
    )

    def _compute_log_count(self):
        for rec in self:
            rec.log_count = len(rec.log_ids)

    @api.model
    def _get_connector(self):
        """Return the singleton Bayut connector record, creating it if needed."""
        connector = self.sudo().search([], order="id asc", limit=1)
        if not connector:
            connector = self.sudo().create({"name": "Bayut Leads Connector"})
        return connector

    @api.model
    def _get_config_settings(self):
        """Fetch Bayut API settings stored in ir.config_parameter."""
        params = self.env["ir.config_parameter"].sudo()
        api_url = (
            params.get_param("bayut_lead_integration.bayut_api_url")
            or "https://leads-api.bayut.com/"
        ).strip()
        api_key = (params.get_param("bayut_lead_integration.bayut_api_key") or "").strip()

        team_id_raw = params.get_param("bayut_lead_integration.bayut_default_team_id")
        user_id_raw = params.get_param("bayut_lead_integration.bayut_default_user_id")
        interval_raw = params.get_param("bayut_lead_integration.bayut_sync_interval", "10")

        team_id = int(team_id_raw) if team_id_raw and str(team_id_raw).isdigit() else False
        user_id = int(user_id_raw) if user_id_raw and str(user_id_raw).isdigit() else False
        try:
            sync_interval = max(int(interval_raw), 1)
        except (ValueError, TypeError):
            sync_interval = 10

        return {
            "api_url": api_url,
            "api_key": api_key,
            "team_id": team_id,
            "user_id": user_id,
            "sync_interval": sync_interval,
        }

    # =========================================================================
    # ISOLATED BAYUT PAYLOAD PARSER
    # =========================================================================
    @api.model
    def _parse_lead(self, raw_lead):
        """Parse a single lead dictionary from the Bayut API response into a
        normalized dictionary used by Odoo CRM.

        TODO: Update the field key mappings below once Bayut Support provides
        the official Leads API response documentation.
        All JSON structure assumptions are isolated inside this single method:
        - Expected top-level response key in cron_sync_leads(): data.get("leads", [])
        - Expected per-lead keys mapped here:
            * id           -> bayut_lead_id (str)
            * type         -> lead_type (email / call_log / phone_view / whatsapp / sms_click / whatsapp_view)
            * client_name  -> client_name (str)
            * email        -> email (str)
            * phone        -> phone (str)
            * message      -> message (str)
            * property_ref -> property_ref (str)
            * created_at   -> created_at (str)
        """
        if not isinstance(raw_lead, dict):
            return {}

        raw_id = (
            raw_lead.get("id")
            or raw_lead.get("lead_id")
            or raw_lead.get("uid")
        )
        lead_type = str(
            raw_lead.get("type")
            or raw_lead.get("lead_type")
            or raw_lead.get("channel")
            or "email"
        ).strip().lower()

        client_name = str(
            raw_lead.get("client_name")
            or raw_lead.get("name")
            or raw_lead.get("sender_name")
            or ""
        ).strip()

        email = str(
            raw_lead.get("email")
            or raw_lead.get("client_email")
            or raw_lead.get("sender_email")
            or ""
        ).strip()

        phone = str(
            raw_lead.get("phone")
            or raw_lead.get("client_phone")
            or raw_lead.get("mobile")
            or raw_lead.get("sender_phone")
            or ""
        ).strip()

        message = str(
            raw_lead.get("message")
            or raw_lead.get("body")
            or raw_lead.get("comments")
            or ""
        ).strip()

        property_ref = str(
            raw_lead.get("property_ref")
            or raw_lead.get("property_reference")
            or raw_lead.get("reference")
            or raw_lead.get("listing_reference")
            or "N/A"
        ).strip()

        created_at = raw_lead.get("created_at") or raw_lead.get("timestamp") or False

        return {
            "bayut_lead_id": str(raw_id).strip() if raw_id is not None and str(raw_id).strip() else "",
            "lead_type": lead_type,
            "client_name": client_name,
            "email": email,
            "phone": phone,
            "message": message,
            "property_ref": property_ref or "N/A",
            "created_at": created_at,
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
            domain = ["|", ("phone", "ilike", norm_phone), ("mobile", "ilike", norm_phone)] if "mobile" in Partner._fields else [("phone", "ilike", norm_phone)]
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
    def _find_matching_property_record(self, property_ref):
        """If eg_property_management (`property.detail`) is installed, try to match the unit."""
        if not property_ref or property_ref == "N/A" or "property.detail" not in self.env:
            return False
        Prop = self.env["property.detail"].sudo()
        domain = ["|", ("code", "=ilike", property_ref), ("name", "=ilike", property_ref)]
        return Prop.search(domain, limit=1)

    # =========================================================================
    # CONNECTION TEST & SYNC EXECUTION
    # =========================================================================
    @api.model
    def test_api_connection(self):
        """Call the configured Bayut API URL with Bearer authentication to verify connectivity."""
        cfg = self._get_config_settings()
        if not cfg["api_url"]:
            return {
                "success": False,
                "message": _("Please configure the Bayut API URL first."),
            }
        if not cfg["api_key"]:
            return {
                "success": False,
                "message": _("Please enter your Bayut API Key before testing the connection."),
            }

        since_dt = fields.Datetime.now() - timedelta(hours=1)
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Accept": "application/json",
        }
        params = {
            "since": since_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        try:
            response = requests.get(
                cfg["api_url"],
                headers=headers,
                params=params,
                timeout=15,
            )
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": _(
                        "Successfully connected to the Bayut Leads API (HTTP 200 OK)."
                    ),
                }
            return {
                "success": False,
                "message": _(
                    "Bayut API responded with HTTP %(status)s: %(body)s",
                    status=response.status_code,
                    body=(response.text or "")[:250],
                ),
            }
        except requests.exceptions.RequestException as exc:
            _logger.warning("Bayut connection test failed: %s", exc)
            return {
                "success": False,
                "message": _("Connection to Bayut API failed: %s") % str(exc),
            }
        except Exception as exc:
            _logger.exception("Unexpected error during Bayut connection test")
            return {
                "success": False,
                "message": _("Unexpected error: %s") % str(exc),
            }

    @api.model
    def cron_sync_leads(self):
        """Scheduled & manual synchronization entry point.
        Calls the Bayut Leads API via GET with Authorization: Bearer <key> and
        since=<last_sync or 24h ago>, creates deduplicated CRM leads, and records a sync log.
        Never raises unhandled exceptions so the cron job never crashes.
        """
        connector = self._get_connector()
        cfg = self._get_config_settings()
        sync_start = fields.Datetime.now()
        LogModel = self.env["bayut.sync.log"].sudo()

        if not cfg["api_url"] or not cfg["api_key"]:
            msg = _(
                "Bayut Sync skipped: Bayut API URL or API Key is not configured in CRM Settings."
            )
            _logger.warning(msg)
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": sync_start,
                "status": "error",
                "leads_created": 0,
                "message": msg,
            })
            return {"status": "error", "leads_created": 0, "message": msg}

        since_dt = connector.last_sync or (sync_start - timedelta(hours=24))
        since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Accept": "application/json",
        }
        params = {
            "since": since_str,
        }

        try:
            response = requests.get(
                cfg["api_url"],
                headers=headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            error_msg = _("Bayut API HTTP request failed: %s") % str(exc)
            _logger.error("Bayut Leads sync error: %s", error_msg)
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": sync_start,
                "status": "error",
                "leads_created": 0,
                "message": error_msg,
            })
            return {"status": "error", "leads_created": 0, "message": error_msg}
        except ValueError as exc:
            error_msg = _("Bayut API returned invalid JSON response: %s") % str(exc)
            _logger.error("Bayut Leads JSON decode error: %s", error_msg)
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": sync_start,
                "status": "error",
                "leads_created": 0,
                "message": error_msg,
            })
            return {"status": "error", "leads_created": 0, "message": error_msg}
        except Exception as exc:
            error_msg = _("Unexpected error calling Bayut API: %s") % str(exc)
            _logger.exception("Unexpected error in Bayut cron_sync_leads")
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": sync_start,
                "status": "error",
                "leads_created": 0,
                "message": error_msg,
            })
            return {"status": "error", "leads_created": 0, "message": error_msg}

        # Extract the list of leads from the JSON response
        if isinstance(payload, dict):
            raw_leads = payload.get("leads", [])
        elif isinstance(payload, list):
            raw_leads = payload
        else:
            raw_leads = []

        if not isinstance(raw_leads, list):
            raw_leads = []

        leads_created = 0
        leads_skipped = 0
        leads_attached = 0
        LeadModel = self.env["crm.lead"].sudo()

        for raw_item in raw_leads:
            try:
                parsed = self._parse_lead(raw_item)
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

                # 1. Primary De-duplication: skip if a crm.lead with the same bayut_lead_id exists
                if bayut_lead_id:
                    existing_by_id = LeadModel.search(
                        [("bayut_lead_id", "=", bayut_lead_id)], limit=1
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

                # If an open lead already exists for the exact same customer & property reference
                # and has no conflicting bayut_lead_id, log the follow-up event onto that lead
                if same_property_lead and same_property_lead.active:
                    if bayut_lead_id and not same_property_lead.bayut_lead_id:
                        same_property_lead.write({"bayut_lead_id": bayut_lead_id})
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

                # 3. Build description and priority (intent signals get low priority '0')
                description_parts = []
                if message:
                    description_parts.append(message)
                if created_at:
                    description_parts.append(f"Bayut Created At: {created_at}")
                if lead_type in INTENT_SIGNAL_TYPES:
                    description_parts.append(INTENT_SIGNAL_NOTE)

                lead_vals = {
                    "name": f"[Bayut {lead_type}] {property_ref}",
                    "contact_name": client_name or False,
                    "email_from": email or False,
                    "phone": phone or False,
                    "description": "\n\n".join(description_parts) if description_parts else False,
                    "team_id": cfg["team_id"] or False,
                    "user_id": cfg["user_id"] or False,
                    "bayut_lead_id": bayut_lead_id or False,
                    "bayut_lead_type": lead_type,
                    "bayut_property_ref": property_ref,
                }

                if partner:
                    lead_vals["partner_id"] = partner.id

                if lead_type in INTENT_SIGNAL_TYPES:
                    lead_vals["priority"] = "0"

                matched_property = self._find_matching_property_record(property_ref)
                if matched_property and "property_id" in LeadModel._fields:
                    lead_vals["property_id"] = matched_property.id

                new_lead = LeadModel.create(lead_vals)
                if lead_type in INTENT_SIGNAL_TYPES:
                    new_lead.message_post(body=INTENT_SIGNAL_NOTE)

                leads_created += 1
            except Exception as item_exc:
                _logger.error(
                    "Failed to import individual Bayut lead %s: %s", raw_item, item_exc
                )

        connector.sudo().write({"last_sync": sync_start})

        summary_msg = _(
            "Sync completed (since %(since)s): %(created)d lead(s) created, "
            "%(attached)d attached to existing leads, %(skipped)d duplicate(s) skipped.",
            since=since_str,
            created=leads_created,
            attached=leads_attached,
            skipped=leads_skipped,
        )
        LogModel.create({
            "connector_id": connector.id,
            "sync_datetime": sync_start,
            "status": "success",
            "leads_created": leads_created,
            "message": summary_msg,
        })
        return {
            "status": "success",
            "leads_created": leads_created,
            "message": summary_msg,
        }

    def action_sync_now(self):
        """Manual trigger from the connector form view."""
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

    def action_view_sync_logs(self):
        """Open the sync logs tree view."""
        self.ensure_one()
        return {
            "name": _("Bayut Sync Logs"),
            "type": "ir.actions.act_window",
            "res_model": "bayut.sync.log",
            "view_mode": "list,form",
            "domain": [("connector_id", "=", self.id)],
            "context": {"default_connector_id": self.id},
        }
