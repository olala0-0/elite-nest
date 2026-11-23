# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BayutListing(models.Model):
    _inherit = "bayut.listing"

    property_id = fields.Many2one(
        comodel_name="property.detail",
        string="Property (Unit)",
        index=True,
        ondelete="set null",
        tracking=True,
        help="Unit in Property Management. When set, unit data (price, size, rooms, "
             "furnishing, type) comes from the property and is read-only here.",
    )
    property_state = fields.Selection(related="property_id.state", string="Unit Status")
    unit_status_alert = fields.Selection(
        selection=[
            ("unpublish", "Unit occupied – unpublish"),
            ("relist", "Ready to re-list"),
        ],
        string="Action Needed",
        tracking=True,
        copy=False,
        index=True,
        help="Set when the unit status changes in Property Management. "
             "The agent publishes / unpublishes manually; the alert clears afterwards.",
    )

    @api.constrains("property_id")
    def _check_one_listing_per_property(self):
        for rec in self.filtered("property_id"):
            dup = self.with_context(active_test=False).sudo().search(
                [("property_id", "=", rec.property_id.id), ("id", "!=", rec.id)], limit=1
            )
            if dup:
                raise ValidationError(_(
                    "Property %(prop)s already has a Bayut listing (%(ref)s).",
                    prop=rec.property_id.name, ref=dup.reference_number,
                ))

    @api.onchange("property_id")
    def _onchange_property_id(self):
        if self.property_id:
            self.update(self.property_id._bayut_unit_vals())

    def write(self, vals):
        if "property_id" in vals and vals["property_id"]:
            prop = self.env["property.detail"].browse(vals["property_id"])
            vals = {**vals, **prop._bayut_unit_vals(), "source_property_ref": prop.id}
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("property_id"):
                prop = self.env["property.detail"].browse(vals["property_id"])
                vals.update(prop._bayut_unit_vals())
                vals["source_property_ref"] = prop.id
        return super().create(vals_list)

    def _bayut_clear_alert(self, alert):
        flagged = self.filtered(lambda l: l.unit_status_alert == alert)
        if flagged:
            flagged.with_context(skip_bayut_auto_sync=True).write({"unit_status_alert": False})
            flagged.activity_ids.filtered(
                lambda a: a.activity_type_id == self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
                and a.summary in (_("Unpublish from Bayut"), _("Ready to re-list on Bayut"))
            ).action_feedback(feedback=_("Done on the Bayut listing."))

    def action_publish_to_bayut(self):
        res = super().action_publish_to_bayut()
        self._bayut_clear_alert("relist")
        return res

    def action_unpublish_from_bayut(self):
        res = super().action_unpublish_from_bayut()
        self._bayut_clear_alert("unpublish")
        return res

    def action_view_property(self):
        self.ensure_one()
        return {
            "name": _("Property"),
            "type": "ir.actions.act_window",
            "res_model": "property.detail",
            "res_id": self.property_id.id,
            "view_mode": "form",
            "target": "current",
        }
