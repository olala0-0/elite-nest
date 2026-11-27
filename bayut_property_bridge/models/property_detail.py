# -*- coding: utf-8 -*-
import logging
import re

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Property states driving the Bayut listing
OCCUPIED_STATES = ("on_rent", "rent", "sold")
VACANT_STATES = ("available", "vacant", "on_sale")

# property.detail fields whose change must refresh the linked listing
PROPERTY_SYNC_TRIGGERS = {
    "property_for", "property_type", "residential_type_id", "bedrooms", "bathrooms", "furnishing",
}

FURNISHING_MAP = {
    "unfurnished": "unfurnished",
    "semi_furnished": "partly_furnished",
    "fully_furnished": "furnished",
}


class PropertyDetail(models.Model):
    _inherit = "property.detail"

    bayut_listing_ids = fields.One2many(
        comodel_name="bayut.listing",
        inverse_name="property_id",
        string="Bayut Listings",
        context={"active_test": False},
    )
    bayut_listing_count = fields.Integer(compute="_compute_bayut_listing_count")

    def _compute_bayut_listing_count(self):
        for rec in self:
            rec.bayut_listing_count = len(rec.sudo().bayut_listing_ids)

    # ------------------------------------------------------------------
    # Mapping: property -> listing (unit data owned by the property)
    # ------------------------------------------------------------------
    def _bayut_size_sqft(self):
        """Initial value only (same as the existing import). Never synced afterwards."""
        self.ensure_one()
        return float(self.total_area or self.usable_area or 0.0)

    def _bayut_price(self):
        self.ensure_one()
        if self.final_price:
            return self.final_price
        return (self.sale_amount if self.property_for == "sale" else self.rent_amount) or 0.0

    def _bayut_property_type(self):
        self.ensure_one()
        res_type = (self.residential_type or "").lower()
        if "villa" in res_type:
            return "Villa"
        if "townhouse" in res_type or "town house" in res_type:
            return "Townhouse"
        if "pent" in res_type:
            return "Penthouse"
        if self.property_type == "commercial" or "office" in res_type:
            return "Office"
        if "shop" in res_type or "retail" in res_type:
            return "Shop"
        if "warehouse" in res_type:
            return "Warehouse"
        return "Apartment"

    def _bayut_unit_vals(self):
        """Unit data the property owns (always overwritten on the listing)."""
        self.ensure_one()
        vals = {
            "purpose": "for-sale" if self.property_for == "sale" else "for-rent",
            "category": "commercial" if self.property_type == "commercial" else "residential",
            "property_type": self._bayut_property_type(),
            "bedrooms": self._bayut_bedrooms(),
            "furnished": FURNISHING_MAP.get(self.furnishing or "unfurnished", "unfurnished"),
        }
        # Bathrooms are hidden on the property form (Studio) -> only sync a real value
        if self.bathrooms:
            vals["bathrooms"] = int(self.bathrooms)
        return vals

    def _bayut_bedrooms(self):
        """Bedrooms field is hidden by Studio here; the count lives in the Residential Type
        name ("STUDIO FLAT", "1 BED ROOM FLAT", "2 BED ROOM FLAT"...)."""
        self.ensure_one()
        if self.bedrooms:
            return str(min(int(self.bedrooms), 7))
        res_type = (self.residential_type or "").lower()
        if "studio" in res_type:
            return "0"
        match = re.search(r"(\d+)\s*(?:bed|br\b|bhk)", res_type)
        return str(min(int(match.group(1)), 7)) if match else "1"

    def _bayut_initial_vals(self):
        """Marketing / location defaults, only used when the listing is created."""
        self.ensure_one()
        project = self.project_id.name if self.project_id else ""
        sub_project = self.sub_project_id.name if self.sub_project_id else ""
        vals = dict(self._bayut_unit_vals())
        vals.update({
            "property_id": self.id,
            "source_property_ref": self.id,
            "name": f"{self.name} - {project}" if project else self.name,
            "reference_number": (self.code or self.name or f"UNIT-{self.id}").strip(),
            "city": self.city or "Dubai",
            "community": project or self.street or "Dubai",
            "sub_community": sub_project or self.street2 or "",
            "building_name": sub_project or project or self.name,
            "description_en": self.website_short_description or self.name,
            # Size and price are separate listing fields: pre-filled once, then edited on the listing only
            "size_sqft": self._bayut_size_sqft(),
            "price": self._bayut_price(),
            "image_1920": self.image_1920,
            "state": "draft",
        })
        return vals

    def _bayut_sync_listings(self, push=True):
        """Write property-owned unit data to the linked listings (only changed values).
        A published listing is pushed to Bayut by bayut.listing.write unless push=False."""
        Listing = self.env["bayut.listing"].sudo()
        count = 0
        for prop in self:
            for listing in prop.sudo().bayut_listing_ids:
                vals = prop._bayut_unit_vals()
                changed = {
                    k: v for k, v in vals.items()
                    if (listing[k] or False) != (v or False)
                    and not (isinstance(v, float) and abs((listing[k] or 0.0) - v) < 0.005)
                }
                if changed:
                    target = listing if push else listing.with_context(skip_bayut_auto_sync=True)
                    target.with_context(bayut_bridge_sync=True).write(changed)
                    count += 1
        return count

    # ------------------------------------------------------------------
    # Status rules
    # ------------------------------------------------------------------
    def _bayut_flag(self, listing, alert, summary, note):
        listing.with_context(skip_bayut_auto_sync=True).write({"unit_status_alert": alert})
        listing.activity_schedule(
            "mail.mail_activity_data_todo",
            summary=summary,
            note=note,
            user_id=(listing.agent_user_id or self.env.user).id,
        )

    def _bayut_apply_state_rules(self):
        """Manual workflow: never publish/unpublish automatically, only alert the agent."""
        for prop in self:
            listings = prop.sudo().bayut_listing_ids
            if not listings:
                continue
            state_label = dict(prop._fields["state"].selection).get(prop.state)
            if prop.state in OCCUPIED_STATES:
                for listing in listings:
                    if listing.state == "published" and listing.unit_status_alert != "unpublish":
                        self._bayut_flag(
                            listing, "unpublish",
                            _("Unpublish from Bayut"),
                            _("Property %(name)s is now %(state)s. Unpublish the Bayut listing.",
                              name=prop.name, state=state_label),
                        )
                    elif listing.state != "published" and listing.unit_status_alert:
                        listing.with_context(skip_bayut_auto_sync=True).write({"unit_status_alert": False})
            elif prop.state in VACANT_STATES:
                for listing in listings:
                    if listing.state == "unpublished" and listing.unit_status_alert != "relist":
                        self._bayut_flag(
                            listing, "relist",
                            _("Ready to re-list on Bayut"),
                            _("Property %s is vacant again. Check the DLD permit, then publish the listing.",
                              prop.name),
                        )
                    elif listing.state == "published" and listing.unit_status_alert == "unpublish":
                        # Unit became vacant again before anyone unpublished: nothing to do any more
                        listing.with_context(skip_bayut_auto_sync=True).write({"unit_status_alert": False})

    def write(self, vals):
        old_states = {rec.id: rec.state for rec in self} if "state" in vals else {}
        res = super().write(vals)
        if self.env.context.get("bayut_bridge_sync"):
            return res
        try:
            with self.env.cr.savepoint():
                if PROPERTY_SYNC_TRIGGERS & set(vals):
                    self._bayut_sync_listings()
                if old_states:
                    self.filtered(lambda r: r.state != old_states.get(r.id))._bayut_apply_state_rules()
        except Exception:
            # Never block saving a property because of the Bayut side
            _logger.exception("Bayut bridge sync failed for properties %s", self.ids)
        return res

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_bayut_listing(self):
        """Open the unit's Bayut listing, creating a draft one from the property if needed."""
        self.ensure_one()
        listing = self.sudo().bayut_listing_ids[:1]
        if not listing:
            Listing = self.env["bayut.listing"].with_context(skip_bayut_auto_sync=True)
            vals = self._bayut_initial_vals()
            # Re-use an unlinked listing with the same reference instead of failing on the unique ref
            orphan = Listing.with_context(active_test=False).search(
                [("property_id", "=", False), ("reference_number", "=ilike", vals["reference_number"])], limit=1
            )
            if orphan:
                orphan.write({"property_id": self.id, "active": True})
                listing = orphan
            else:
                listing = Listing.create(vals)
        return {
            "name": _("Bayut Listing"),
            "type": "ir.actions.act_window",
            "res_model": "bayut.listing",
            "res_id": listing.id,
            "view_mode": "form",
            "target": "current",
        }
