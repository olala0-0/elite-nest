from odoo import fields, models


class PropertyUtilityService(models.Model):
    _name = "property.utility.service"
    _description = "Utility Service"

    service_id = fields.Many2one(comodel_name='property.service', string="Service")
    service_type = fields.Selection([("once", "Once"), ("recurring", "Recurring")], string="Service Type")
    cost = fields.Monetary(string="Cost", currency_field="currency_id")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id.id)
    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    rent_contract_id = fields.Many2one(comodel_name="rent.contract", string="Rent Contract")
    invoice_id = fields.Many2one(comodel_name='account.move', string='Bill / Invoice')
