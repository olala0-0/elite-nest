from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    rent_contract_id = fields.Many2one(comodel_name='rent.contract', string='Contract')
    sale_contract_id = fields.Many2one(comodel_name='sale.contract', string='Contract')
