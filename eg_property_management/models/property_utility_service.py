from odoo import fields, models


class PropertyUtilityService(models.Model):
    _name = "property.utility.service"
    _description = "Utility Service"

    service_id = fields.Many2one(comodel_name='property.service', string="Service")
    product_id = fields.Many2one(comodel_name='product.product', string="Invoice Product", check_company=False)
    service_type = fields.Selection([("once", "Once"), ("recurring", "Recurring")], string="Service Type")
    cost = fields.Monetary(string="Cost", currency_field="currency_id")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id.id)
    property_id = fields.Many2one(comodel_name="property.detail", string="Property", check_company=False)
    rent_contract_id = fields.Many2one(comodel_name="rent.contract", string="Rent Contract", check_company=False)
    invoice_id = fields.Many2one(comodel_name='account.move', string='Bill / Invoice', check_company=False)
