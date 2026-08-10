from odoo import models, fields, api


class RentInstallment(models.Model):
    _name = 'rent.installment'
    _description = 'Rent Installment'

    rent_contract_id = fields.Many2one(comodel_name='rent.contract', string='Contract')
    invoice_date = fields.Date(string='Invoice Date', default=fields.Date.context_today)
    payment_type = fields.Selection(
        [('rent', 'Rent'), ('deposit', 'Deposit'), ('maintenance', 'Maintenance'), ('penalty', 'Penalty'),
         ('broker_bill', 'Broker Bill'), ('utility', 'Utility'), ('dilapidation', 'Dilapidation'),
         ('shortfall_rent', 'Shortfall Rent'), ('ejari_fee', 'Ejari Fee'), ('admin_charge', 'Admin Charge'),
         ('commission', 'Commission'), ('parking_fee', 'Parking Fee')], string='Payment Type', default='rent')
    description = fields.Char(string='Description')
    amount = fields.Monetary(string='Amount')
    invoice_id = fields.Many2one(comodel_name='account.move', string='Invoice Number')
    currency_id = fields.Many2one(comodel_name='res.currency', related='rent_contract_id.currency_id',
                                  string='Currency', store=True, readonly=True)
