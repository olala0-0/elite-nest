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
            # Counts the maintenance requests associated with this specific ticket
            rec.maintenance_count = self.env["maintenance.request"].search_count([
                ("ticket_id", "=", rec.id)
            ]) if rec.id else 0

    @api.model_create_multi
    def create(self, vals_list):
        """ Automatically assign Property/Unit if the ticket is submitted 
        by a portal tenant who has an active contract. """
        for vals in vals_list:
            if not vals.get('property_id') and vals.get('partner_id'):
                # Look up active rental contracts for this tenant
                contract = self.env['rent.contract'].sudo().search([
                    ('partner_id', '=', vals['partner_id'])
                ], limit=1)
                if contract and contract.property_id:
                    vals['property_id'] = contract.property_id.id
                else:
                    # Fallback to check sale contracts if rent is not found
                    sale_contract = self.env['sale.contract'].sudo().search([
                        ('partner_id', '=', vals['partner_id'])
                    ], limit=1)
                    if sale_contract and sale_contract.property_id:
                        vals['property_id'] = sale_contract.property_id.id
        return super(HelpdeskTicket, self).create(vals_list)

    @api.onchange('partner_id')
    def _onchange_partner_id_set_property(self):
        """ Auto-populate property details when the partner is selected manually in backend. """
        if self.partner_id:
            contract = self.env['rent.contract'].search([('partner_id', '=', self.partner_id.id)], limit=1)
            if contract and contract.property_id:
                self.property_id = contract.property_id.id
            else:
                sale_contract = self.env['sale.contract'].search([('partner_id', '=', self.partner_id.id)], limit=1)
                if sale_contract and sale_contract.property_id:
                    self.property_id = sale_contract.property_id.id

    def action_create_maintenance_request(self):
        self.ensure_one()

        if not self.property_id:
            raise UserError("Please set a Property / Unit before creating a Maintenance Request.")

        maintenance_request = self.env["maintenance.request"].create({
            "name": f"Maintenance for {self.property_id.name} - {self.name}",
            "property_id": self.property_id.id,
            "ticket_id": self.id,
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
            "view_mode": "tree,form",
            "domain": [("ticket_id", "=", self.id)],
            "context": {
                "default_property_id": self.property_id.id,
                "default_ticket_id": self.id,
            }
        }
