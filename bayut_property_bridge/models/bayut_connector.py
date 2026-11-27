# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class BayutConnector(models.Model):
    _inherit = "bayut.connector"

    @api.model
    def _auto_sync_from_odoo_properties(self):
        """Cron safety net: re-apply property-owned unit data to every linked listing.
        (Normal path is instant sync on property save.)"""
        props = self.env["property.detail"].sudo().search([("bayut_listing_ids", "!=", False)])
        return props._bayut_sync_listings(push=False)

    def action_import_from_odoo_properties(self):
        """Create a draft listing for every unit that has none; refresh the linked ones."""
        Property = self.env["property.detail"].sudo()
        Listing = self.env["bayut.listing"].sudo().with_context(skip_bayut_auto_sync=True)
        created = 0
        for prop in Property.search([("bayut_listing_ids", "=", False)]):
            ref = (prop.code or prop.name or f"UNIT-{prop.id}").strip()
            orphan = Listing.with_context(active_test=False).search(
                [("property_id", "=", False), ("reference_number", "=ilike", ref)], limit=1
            )
            if orphan:
                orphan.write({"property_id": prop.id})
            else:
                Listing.create(prop._bayut_initial_vals())
                created += 1
        updated = Property.search([("bayut_listing_ids", "!=", False)])._bayut_sync_listings(push=False)

        msg = _(
            "Created %(created)d draft listing(s) and refreshed %(updated)d linked listing(s) from Properties.",
            created=created, updated=updated,
        )
        self.env["bayut.sync.log"].sudo().create({
            "connector_id": self._get_connector().id,
            "sync_datetime": fields.Datetime.now(),
            "sync_type": "listings",
            "status": "success",
            "listings_synced": created + updated,
            "message": msg,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Properties → Bayut Listings"), "message": msg,
                       "type": "success", "sticky": False},
        }

    @api.model
    def _find_matching_property_record(self, property_ref):
        """Prefer the property linked to the matching listing."""
        listing = self._find_matching_bayut_listing(property_ref)
        if listing and listing.property_id:
            return listing.property_id
        return super()._find_matching_property_record(property_ref)
