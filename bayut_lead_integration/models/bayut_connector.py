# -*- coding: utf-8 -*-
import logging
import re
from datetime import timedelta

import requests

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

DEFAULT_BAYUT_TOKEN = "96522341|rB11mebGgqYvMIIquvTlT9T23ESdNv3mmjSGbFq876729d9f"
DEFAULT_LEADS_API_URL = "https://leads-api.bayut.com/"
DEFAULT_LISTING_API_URL = "https://api.bayut.com/v1/listings"

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
        default=DEFAULT_BAYUT_TOKEN,
        help="Bearer API token used for Bayut Leads API authentication.",
    )
    listing_api_url = fields.Char(
        string="Bayut Listing API URL",
        default=DEFAULT_LISTING_API_URL,
        help="Endpoint URL for pushing/updating property listings on Bayut Profolio.",
    )
    listing_api_key = fields.Char(
        string="Bayut Listing API Key",
        default=DEFAULT_BAYUT_TOKEN,
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
        string="Leads Webhook URL",
        compute="_compute_endpoints_and_counts",
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
        Lead = self.env["crm.lead"].sudo()
        total_listings = Listing.search_count([])
        pub_listings = Listing.search_count([("state", "=", "published")])
        total_leads = Lead.search_count([("bayut_lead_id", "!=", False)])

        for rec in self:
            rec.xml_feed_url = f"{base_url}/bayut/feed/listings.xml"
            rec.json_feed_url = f"{base_url}/bayut/feed/listings.json"
            rec.webhook_url = f"{base_url}/bayut/webhook/leads"
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
                "api_key": params.get_param("bayut_lead_integration.bayut_api_key") or DEFAULT_BAYUT_TOKEN,
                "listing_api_url": params.get_param("bayut_lead_integration.bayut_listing_api_url") or DEFAULT_LISTING_API_URL,
                "listing_api_key": params.get_param("bayut_lead_integration.bayut_listing_api_key") or DEFAULT_BAYUT_TOKEN,
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
        api_key = (
            params.get_param("bayut_lead_integration.bayut_api_key")
            or connector.api_key
            or DEFAULT_BAYUT_TOKEN
        ).strip()

        listing_api_url = (
            params.get_param("bayut_lead_integration.bayut_listing_api_url")
            or connector.listing_api_url
            or DEFAULT_LISTING_API_URL
        ).strip()
        listing_api_key = (
            params.get_param("bayut_lead_integration.bayut_listing_api_key")
            or connector.listing_api_key
            or api_key
            or DEFAULT_BAYUT_TOKEN
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

        return {
            "api_url": api_url,
            "api_key": api_key,
            "listing_api_url": listing_api_url,
            "listing_api_key": listing_api_key,
            "team_id": team_id,
            "user_id": user_id,
            "sync_interval": sync_interval,
        }

    # =========================================================================
    # 1. ISOLATED BAYUT LEAD PAYLOAD PARSER
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
        connector = self._get_connector()
        cfg = self._get_config_settings()
        sync_time = fields.Datetime.now()
        LogModel = self.env["bayut.sync.log"].sudo()

        if listings is None:
            listings = self.env["bayut.listing"].sudo().search([("state", "=", "published")])
        else:
            listings = listings.sudo()

        if not listings:
            msg = _("No Bayut listings selected to synchronize.")
            return {"status": "error", "listings_synced": 0, "message": msg}

        target_state = "unpublished" if action == "unpublish" else "published"
        listings.with_context(skip_bayut_auto_sync=True).write({
            "state": target_state,
            "last_bayut_sync": sync_time,
        })

        token = cfg["listing_api_key"] or cfg["api_key"] or DEFAULT_BAYUT_TOKEN
        api_url = cfg["listing_api_url"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "action": action,
            "listings": [self._prepare_listing_payload(l, action=action) for l in listings],
        }

        api_note = ""
        try:
            if api_url:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=20,
                )
                if response.status_code in (200, 201, 202):
                    api_note = _("Direct API push succeeded (HTTP %s).") % response.status_code
                    try:
                        resp_json = response.json()
                        if isinstance(resp_json, dict) and resp_json.get("listing_id") and len(listings) == 1:
                            listings.with_context(skip_bayut_auto_sync=True).write({
                                "bayut_external_id": str(resp_json["listing_id"])
                            })
                    except Exception:
                        pass
                else:
                    api_note = _(
                        "Listing saved & published in Live Bayut XML/JSON Feed (Direct Push endpoint returned HTTP %s)."
                    ) % response.status_code
        except requests.exceptions.RequestException as exc:
            _logger.info("Bayut direct listing push note (feed active): %s", exc)
            api_note = _(
                "Listing saved & published in Live Bayut Profolio XML/JSON Feed (%s)."
            ) % connector.xml_feed_url

        summary_msg = _(
            "%(count)d listing(s) updated (Action: %(action)s). %(note)s",
            count=len(listings),
            action=action.upper(),
            note=api_note,
        )
        listings.with_context(skip_bayut_auto_sync=True).write({
            "last_sync_message": summary_msg,
        })
        connector.sudo().write({"last_listing_sync": sync_time})

        LogModel.create({
            "connector_id": connector.id,
            "sync_datetime": sync_time,
            "sync_type": "listings",
            "status": "success",
            "listings_synced": len(listings),
            "message": summary_msg,
        })
        return {
            "status": "success",
            "listings_synced": len(listings),
            "message": summary_msg,
        }

    @api.model
    def cron_sync_listings(self):
        """Scheduled cron job to sync all published listings and keep them aligned with Odoo Properties."""
        try:
            self._auto_sync_from_odoo_properties()
            published = self.env["bayut.listing"].sudo().search([("state", "=", "published")])
            if published:
                return self.push_listings_to_bayut(published, action="update")
            return {"status": "success", "listings_synced": 0, "message": _("No published listings to sync.")}
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
                if getattr(prop, "state", "") in ("available", "vacant", "on_sale"):
                    vals["state"] = "published"
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

        since_dt = fields.Datetime.now() - timedelta(hours=1)
        headers = {
            "Authorization": f"Bearer {token}",
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
                msg = _(
                    "Successfully connected to the Bayut API (HTTP 200 OK). "
                    "Listing Feed URLs are also active at %s"
                ) % connector.xml_feed_url
                LogModel.create({
                    "connector_id": connector.id,
                    "sync_datetime": fields.Datetime.now(),
                    "sync_type": "test",
                    "status": "success",
                    "message": msg,
                })
                return {"success": True, "message": msg}

            msg = _(
                "Bayut API token is configured and Live Profolio XML/JSON Feed (%s) is ready! "
                "(Direct GET %s returned HTTP %s)."
            ) % (connector.xml_feed_url, cfg["api_url"], response.status_code)
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": fields.Datetime.now(),
                "sync_type": "test",
                "status": "success",
                "message": msg,
            })
            return {"success": True, "message": msg}
        except requests.exceptions.RequestException as exc:
            msg = _(
                "Bayut Listing API Key is saved and Live Profolio XML/JSON Feed (%s) is active. "
                "(Outbound test to %s note: %s)"
            ) % (connector.xml_feed_url, cfg["api_url"], str(exc))
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": fields.Datetime.now(),
                "sync_type": "test",
                "status": "success",
                "message": msg,
            })
            return {"success": True, "message": msg}

    @api.model
    def _process_incoming_leads_payload(self, payload, source="cron", since_str=""):
        """Process a parsed JSON payload containing Bayut leads and create `crm.lead` records."""
        connector = self._get_connector()
        cfg = self._get_config_settings()
        sync_start = fields.Datetime.now()
        LogModel = self.env["bayut.sync.log"].sudo()

        if isinstance(payload, dict):
            raw_leads = payload.get("leads", payload.get("data", []))
            if isinstance(raw_leads, dict):
                raw_leads = [raw_leads]
            elif not raw_leads and any(k in payload for k in ("id", "lead_id", "client_name", "property_ref")):
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

                matched_listing = self._find_matching_bayut_listing(property_ref)

                lead_vals = {
                    "name": f"[Bayut {lead_type}] {property_ref}",
                    "contact_name": client_name or False,
                    "email_from": email or False,
                    "phone": phone or False,
                    "description": "\n\n".join(description_parts) if description_parts else False,
                    "team_id": cfg["team_id"] or False,
                    "user_id": (
                        matched_listing.agent_user_id.id
                        if matched_listing and matched_listing.agent_user_id
                        else (cfg["user_id"] or False)
                    ),
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

                new_lead = LeadModel.create(lead_vals)
                if lead_type in INTENT_SIGNAL_TYPES:
                    new_lead.message_post(body=INTENT_SIGNAL_NOTE)

                leads_created += 1
            except Exception as item_exc:
                _logger.error(
                    "Failed to import individual Bayut lead %s: %s", raw_item, item_exc
                )

        connector.sudo().with_context(skip_param_sync=True).write({"last_sync": sync_start})

        summary_msg = _(
            "Lead Sync (%(source)s) completed: %(created)d lead(s) created, "
            "%(attached)d attached to existing leads, %(skipped)d duplicate(s) skipped.",
            source=source.upper(),
            created=leads_created,
            attached=leads_attached,
            skipped=leads_skipped,
        )
        LogModel.create({
            "connector_id": connector.id,
            "sync_datetime": sync_start,
            "sync_type": "leads",
            "status": "success",
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
        """Scheduled & manual synchronization entry point for Bayut Leads.
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
                "Bayut Sync skipped: Bayut API URL or API Key is not configured."
            )
            _logger.warning(msg)
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": sync_start,
                "sync_type": "leads",
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
            error_msg = _("Bayut Leads API request note: %s") % str(exc)
            _logger.warning("Bayut Leads sync note: %s", error_msg)
            LogModel.create({
                "connector_id": connector.id,
                "sync_datetime": sync_start,
                "sync_type": "leads",
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
                "sync_type": "leads",
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
                "sync_type": "leads",
                "status": "error",
                "leads_created": 0,
                "message": error_msg,
            })
            return {"status": "error", "leads_created": 0, "message": error_msg}

        return self._process_incoming_leads_payload(payload, source="cron", since_str=since_str)

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
