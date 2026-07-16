from odoo import models, fields, api
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    property_id = fields.Many2one(comodel_name="property.detail", string="Property / Unit")
    maintenance_request_id = fields.Many2one(
        comodel_name="maintenance.request", 
        string="Maintenance Request",
        readonly=True, 
        copy=False
    )
    maintenance_count = fields.Integer(
        string="Maintenance Requests", 
        compute="_compute_maintenance_count"
    )

    @api.depends("property_id")
    def _compute_maintenance_count(self):
        for rec in self:
            rec.maintenance_count = self.env["maintenance.request"].search_count([
                ("property_id", "=", rec.property_id.id)
            ]) if rec.property_id else 0

    def action_create_maintenance_request(self):
        self.ensure_one()

        if not self.property_id:
            raise UserError("Please set a Property / Unit before creating a Maintenance Request.")

        maintenance_request = self.env["maintenance.request"].create({
            "name": f"Maintenance for {self.property_id.name} - {self.name}",
            "property_id": self.property_id.id,
            "request_date": fields.Date.context_today(self),
        })

        self.maintenance_request_id = maintenance_request.id

        return {
            "name": "Maintenance Request",
            "type": "ir.actions.act_window",
            "res_model": "maintenance.request",
            "res_id": maintenance_request.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_maintenance_requests(self):
        self.ensure_one()
        return {
            "name": "Maintenance Requests",
            "type": "ir.actions.act_window",
            "res_model": "maintenance.request",
            "view_mode": "list,form",
            "domain": [("property_id", "=", self.property_id.id)],
        }
