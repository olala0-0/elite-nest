# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BayutListingImage(models.Model):
    _name = "bayut.listing.image"
    _description = "Bayut Property Listing Image"
    _order = "sequence asc, id asc"

    listing_id = fields.Many2one(
        comodel_name="bayut.listing",
        string="Listing",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Title / Caption")
    image = fields.Image(string="Image", max_width=1920, max_height=1920)
    external_url = fields.Char(
        string="Image URL",
        compute="_compute_external_url",
        store=False,
    )

    def _compute_external_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
        for rec in self:
            if rec.id:
                rec.external_url = f"{base_url}/web/image/bayut.listing.image/{rec.id}/image"
            else:
                rec.external_url = ""


class BayutListing(models.Model):
    _name = "bayut.listing"
    _description = "Bayut & Profolio Property Listing"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Listing Title (English)",
        required=True,
        tracking=True,
    )
    title_ar = fields.Char(
        string="Listing Title (Arabic)",
        tracking=True,
    )
    reference_number = fields.Char(
        string="Property Reference",
        required=True,
        copy=False,
        index=True,
        default=lambda self: _("New"),
        tracking=True,
        help="Unique agency reference code used on Bayut Profolio (e.g. EN-101).",
    )
    bayut_external_id = fields.Char(
        string="Bayut Listing ID",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help="External Listing ID returned by Bayut API after publishing.",
    )
    permit_number = fields.Char(
        string="DLD / RERA Permit Number",
        tracking=True,
        help="Trakheesi / DLD / Madmoun permit number required by Bayut Profolio.",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("published", "Published on Bayut"),
            ("unpublished", "Unpublished"),
            ("error", "Sync Error"),
        ],
        string="Bayut Status",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    active = fields.Boolean(default=True)

    # Purpose & Category
    purpose = fields.Selection(
        selection=[
            ("for-rent", "For Rent"),
            ("for-sale", "For Sale"),
        ],
        string="Purpose",
        default="for-rent",
        required=True,
        tracking=True,
    )
    category = fields.Selection(
        selection=[
            ("residential", "Residential"),
            ("commercial", "Commercial"),
        ],
        string="Category",
        default="residential",
        required=True,
        tracking=True,
    )
    property_type = fields.Selection(
        selection=[
            ("Apartment", "Apartment / Flat"),
            ("Villa", "Villa"),
            ("Townhouse", "Townhouse"),
            ("Penthouse", "Penthouse"),
            ("Hotel Apartment", "Hotel Apartment"),
            ("Residential Building", "Residential Building"),
            ("Residential Plot", "Residential Plot"),
            ("Office", "Office"),
            ("Shop", "Shop / Retail"),
            ("Warehouse", "Warehouse"),
            ("Commercial Building", "Commercial Building"),
            ("Commercial Plot", "Commercial Plot"),
        ],
        string="Property Type",
        default="Apartment",
        required=True,
        tracking=True,
    )

    # Pricing & Specifications
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    price = fields.Monetary(
        string="Price (AED)",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    rent_frequency = fields.Selection(
        selection=[
            ("yearly", "Yearly"),
            ("monthly", "Monthly"),
            ("weekly", "Weekly"),
            ("daily", "Daily"),
        ],
        string="Rent Frequency",
        default="yearly",
        tracking=True,
    )
    bedrooms = fields.Selection(
        selection=[
            ("0", "Studio"),
            ("1", "1 Bedroom"),
            ("2", "2 Bedrooms"),
            ("3", "3 Bedrooms"),
            ("4", "4 Bedrooms"),
            ("5", "5 Bedrooms"),
            ("6", "6 Bedrooms"),
            ("7", "7+ Bedrooms"),
        ],
        string="Bedrooms",
        default="1",
        tracking=True,
    )
    bathrooms = fields.Integer(string="Bathrooms", default=1, tracking=True)
    size_sqft = fields.Float(string="Size (Sqft)", tracking=True)
    parking_spaces = fields.Integer(string="Parking Spaces", default=1)
    furnished = fields.Selection(
        selection=[
            ("unfurnished", "Unfurnished"),
            ("partly_furnished", "Semi-Furnished"),
            ("furnished", "Fully Furnished"),
        ],
        string="Furnishing",
        default="unfurnished",
        tracking=True,
    )
    completion_status = fields.Selection(
        selection=[
            ("completed", "Ready / Completed"),
            ("off_plan", "Off-Plan"),
        ],
        string="Completion Status",
        default="completed",
    )

    # Location Details
    city = fields.Char(string="City / Emirate", default="Dubai", required=True, tracking=True)
    community = fields.Char(string="Community / Locality", tracking=True, help="e.g. Dubai Marina, Business Bay")
    sub_community = fields.Char(string="Sub-Community", tracking=True)
    building_name = fields.Char(string="Tower / Building Name", tracking=True)
    bayut_location_id = fields.Char(string="Bayut Location ID", help="Optional location ID from Bayut Profolio.")
    latitude = fields.Float(string="Latitude", digits=(10, 7))
    longitude = fields.Float(string="Longitude", digits=(10, 7))

    # Descriptions & Media
    description_en = fields.Text(string="Description (English)", tracking=True)
    description_ar = fields.Text(string="Description (Arabic)")
    image_1920 = fields.Image(string="Main Cover Image", max_width=1920, max_height=1920)
    image_ids = fields.One2many(
        comodel_name="bayut.listing.image",
        inverse_name="listing_id",
        string="Gallery Images",
    )
    video_url = fields.Char(string="Video Tour URL")
    virtual_tour_url = fields.Char(string="360 Virtual Tour URL")

    # Portal Target & Agent Info
    publish_on_bayut = fields.Boolean(string="Publish on Bayut", default=True, tracking=True)

    agent_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned Agent (User)",
        default=lambda self: self.env.user,
        tracking=True,
    )
    agent_name = fields.Char(
        string="Listing Agent Name",
        compute="_compute_agent_details",
        store=True,
        readonly=False,
    )
    agent_email = fields.Char(
        string="Listing Agent Email",
        compute="_compute_agent_details",
        store=True,
        readonly=False,
    )
    agent_phone = fields.Char(
        string="Listing Agent Phone",
        compute="_compute_agent_details",
        store=True,
        readonly=False,
    )
    agent_brn = fields.Char(string="Agent RERA BRN")

    # Sync Metadata & Linked Leads
    source_property_ref = fields.Integer(
        string="Linked Odoo Property ID",
        index=True,
        readonly=True,
        help="ID of the corresponding property.detail record if imported from Property Management.",
    )
    last_bayut_sync = fields.Datetime(string="Last Synced to Bayut", readonly=True)
    last_sync_message = fields.Text(string="Last Sync Response", readonly=True)
    lead_ids = fields.One2many(
        comodel_name="crm.lead",
        inverse_name="bayut_listing_id",
        string="Bayut Leads",
    )
    lead_count = fields.Integer(string="Leads", compute="_compute_lead_count")

    @api.constrains("reference_number")
    def _check_unique_reference_number(self):
        for rec in self:
            if not rec.reference_number:
                continue
            duplicate = self.sudo().search(
                [
                    ("reference_number", "=", rec.reference_number),
                    ("id", "!=", rec.id),
                ],
                limit=1,
            )
            if duplicate:
                raise UserError(
                    _("Property Reference '%s' is already used on another Bayut listing.")
                    % rec.reference_number
                )

    @api.depends("agent_user_id")
    def _compute_agent_details(self):
        for rec in self:
            if rec.agent_user_id:
                rec.agent_name = rec.agent_name or rec.agent_user_id.name
                rec.agent_email = rec.agent_email or rec.agent_user_id.email or rec.agent_user_id.login
                rec.agent_phone = rec.agent_phone or rec.agent_user_id.phone
            else:
                rec.agent_name = rec.agent_name or ""
                rec.agent_email = rec.agent_email or ""
                rec.agent_phone = rec.agent_phone or ""

    def _compute_lead_count(self):
        Lead = self.env["crm.lead"].sudo()
        for rec in self:
            domain = ["|", ("bayut_listing_id", "=", rec.id), ("bayut_property_ref", "=", rec.reference_number)]
            rec.lead_count = Lead.search_count(domain)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference_number") or vals.get("reference_number") == _("New"):
                seq = self.env["ir.sequence"].next_by_code("bayut.listing") or "BYT-0001"
                vals["reference_number"] = seq
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        # Automatically push updates to Bayut when a published listing's details are edited
        sync_trigger_fields = {
            "name", "title_ar", "permit_number", "purpose", "category", "property_type",
            "price", "rent_frequency", "bedrooms", "bathrooms", "size_sqft", "furnished",
            "city", "community", "sub_community", "building_name", "description_en",
            "description_ar", "publish_on_bayut", "agent_name",
            "agent_email", "agent_phone",
        }
        if not self.env.context.get("skip_bayut_auto_sync") and (sync_trigger_fields & set(vals.keys())):
            published_listings = self.filtered(lambda l: l.state == "published")
            if published_listings:
                try:
                    self.env["bayut.connector"].sudo().push_listings_to_bayut(
                        published_listings, action="update"
                    )
                except Exception as exc:
                    _logger.warning("Auto-sync to Bayut on listing write failed: %s", exc)
        return res

    def _to_bayut_dict(self):
        """Serialize this listing into the normalized dictionary used by both
        the Bayut Listing Push API and the XML/JSON feed controllers."""
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
        images = []
        if self.image_1920 and self.id:
            images.append(f"{base_url}/web/image/bayut.listing/{self.id}/image_1920")
        for img in self.image_ids:
            if img.id:
                images.append(f"{base_url}/web/image/bayut.listing.image/{img.id}/image")

        portals = ["bayut"] if self.publish_on_bayut else []

        return {
            "id": self.bayut_external_id or False,
            "reference_number": self.reference_number,
            "permit_number": self.permit_number or "",
            "Purpose": "Rent" if self.purpose == "for-rent" else "Buy",
            "purpose": self.purpose,
            "category": self.category,
            "property_type": self.property_type,
            "status": "active" if self.state == "published" else "inactive",
            "price": float(self.price or 0.0),
            "currency": self.currency_id.name or "AED",
            "rent_frequency": self.rent_frequency if self.purpose == "for-rent" else False,
            "bedrooms": int(self.bedrooms or 0),
            "bathrooms": int(self.bathrooms or 0),
            "size_sqft": float(self.size_sqft or 0.0),
            "parking_spaces": int(self.parking_spaces or 0),
            "furnished": self.furnished or "unfurnished",
            "completion_status": self.completion_status or "completed",
            "city": self.city or "Dubai",
            "community": self.community or "",
            "sub_community": self.sub_community or "",
            "building_name": self.building_name or "",
            "location_id": self.bayut_location_id or False,
            "latitude": self.latitude or False,
            "longitude": self.longitude or False,
            "title_en": self.name or "",
            "title_ar": self.title_ar or "",
            "description_en": self.description_en or "",
            "description_ar": self.description_ar or "",
            "images": images,
            "video_url": self.video_url or "",
            "virtual_tour_url": self.virtual_tour_url or "",
            "portals": portals or ["bayut"],
            "agent_name": self.agent_name or "",
            "agent_email": self.agent_email or "",
            "agent_phone": self.agent_phone or "",
            "agent_brn": self.agent_brn or "",
            "updated_at": (self.write_date or fields.Datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
        }

    # =========================================================================
    # USER ACTIONS ON LISTING FORM / LIST
    # =========================================================================
    def action_publish_to_bayut(self):
        """Publish and push selected listing(s) to Bayut Profolio."""
        connector = self.env["bayut.connector"].sudo()._get_connector()
        result = connector.push_listings_to_bayut(self, action="publish")
        notif_type = "success" if result.get("status") == "success" else "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Bayut Listing Sync"),
                "message": result.get("message", ""),
                "type": notif_type,
                "sticky": notif_type != "success",
            },
        }

    def action_update_on_bayut(self):
        """Push updated details for selected listing(s) to Bayut Profolio."""
        connector = self.env["bayut.connector"].sudo()._get_connector()
        result = connector.push_listings_to_bayut(self, action="update")
        notif_type = "success" if result.get("status") == "success" else "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Bayut Listing Update"),
                "message": result.get("message", ""),
                "type": notif_type,
                "sticky": notif_type != "success",
            },
        }

    def action_unpublish_from_bayut(self):
        """Unpublish selected listing(s) from Bayut Profolio."""
        connector = self.env["bayut.connector"].sudo()._get_connector()
        result = connector.push_listings_to_bayut(self, action="unpublish")
        notif_type = "success" if result.get("status") == "success" else "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Bayut Listing Unpublish"),
                "message": result.get("message", ""),
                "type": notif_type,
                "sticky": False,
            },
        }

    def action_set_draft(self):
        self.with_context(skip_bayut_auto_sync=True).write({"state": "draft"})

    def action_view_leads(self):
        self.ensure_one()
        return {
            "name": _("Bayut Leads — %s") % self.reference_number,
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "domain": [
                "|",
                ("bayut_listing_id", "=", self.id),
                ("bayut_property_ref", "=", self.reference_number),
            ],
            "context": {
                "default_bayut_listing_id": self.id,
                "default_bayut_property_ref": self.reference_number,
            },
        }
