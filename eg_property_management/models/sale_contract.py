from odoo import models, fields, api
from datetime import date
from odoo.exceptions import UserError


class SaleContract(models.Model):
    _name = "sale.contract"
    _description = "Sale Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Sequence', default=lambda self: 'New', readonly=True)
    create_date = fields.Date(string="Create Date", default=fields.Date.today, readonly=True)
    sale_contract = fields.Binary(string="Upload Contract File", attachment=True)

    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 default=lambda self: self.env.company)
    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    property_type = fields.Selection([("land", "Land"), ("residential", "Residential"), ("commercial", "Commercial"),
                                      ("industrial", "Industrial")], string="Property Type", default='land')

    residential_type_id = fields.Many2one(
        comodel_name="property.residential.type",
        string="Residential Type",
        related="property_id.residential_type_id",
        store=True,
        readonly=True,
    )
    residential_type = fields.Char(related="residential_type_id.name", string="Residential Type Text", store=True)
    property_for = fields.Selection([("sale", "Sale"), ("rent", "Rent")], string="Property For", default='sale')

    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street Line 2")
    city = fields.Char(string="City")
    state_id = fields.Many2one(comodel_name="res.country.state", string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one(comodel_name="res.country", string="Country")

    total_area = fields.Float(string="Total Area (ft²)")
    sell_amount = fields.Monetary(string="Sell Amount", currency_field="currency_id")
    total_amount = fields.Monetary(string="Total Amount", currency_field="currency_id",
                                   compute="_compute_total_amount", readonly=False)

    lead_id = fields.Many2one(comodel_name='crm.lead', string="Source Lead")

    tenant_id = fields.Many2one(comodel_name="res.partner", string="Tenant / Customer")
    tenant_phone = fields.Char(related="tenant_id.phone", string="Tenant Phone", readonly=True)
    tenant_email = fields.Char(related="tenant_id.email", string="Tenant Email", readonly=True)

    landlord_id = fields.Many2one(comodel_name="res.partner", string="Landlord")
    landlord_phone = fields.Char(related="landlord_id.phone", string="Landlord Phone", readonly=True)
    landlord_email = fields.Char(related="landlord_id.email", string="Landlord Email", readonly=True)

    user_id = fields.Many2one(comodel_name='res.users', string='Responsible User', default=lambda self: self.env.user)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")

    broker_id = fields.Many2one(comodel_name="res.partner", string="Broker / Agent",
                                domain="[('is_company','=',False)]")
    broker_phone = fields.Char(related="broker_id.phone", string="Broker Phone", readonly=True)
    broker_email = fields.Char(related="broker_id.email", string="Broker Email", readonly=True)
    broker_commission = fields.Monetary(string="Broker Commission", currency_field="currency_id", default=0.0)
    broker_bill_id = fields.Many2one(comodel_name="account.move", string="Broker Bill", readonly=True, copy=False)

    has_broker_bill = fields.Boolean(string="Has Broker Bill", compute="_compute_has_broker_bill", store=False)

    state = fields.Selection([('draft', 'Draft'), ('booked', 'Booked'), ('sold', 'Sold'), ('refund', 'Refund')],
                             string="Status", default='draft', tracking=True)
    invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            val['name'] = self.env['ir.sequence'].next_by_code('sale.contract') or 'New'
        return super(SaleContract, self).create(vals_list)

    @api.onchange('sell_amount', 'total_area')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.sell_amount * record.total_area if record.sell_amount and record.total_area else 0

    def action_state_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.property_id.state = 'on_sale'

    def action_state_booked(self):
        for rec in self:
            rec.state = 'booked'

    def action_state_sold(self):
        for rec in self:
            rec.state = 'sold'
            rec.property_id.state = 'sold'

            if rec.invoice_id:
                continue

            if not rec.tenant_id:
                raise UserError("Please select a Tenant / Customer before creating an invoice.")

            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': rec.tenant_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
                'currency_id': rec.currency_id.id,
                'property_id': rec.property_id.id,
                'invoice_origin': rec.name,
                'invoice_line_ids': [(0, 0, {
                    'name': f"Sale Contract for {rec.property_id.name or 'Property'}",
                    'quantity': 1,
                    'price_unit': rec.total_amount or 0.0,
                    'tax_ids': [],
                })],
            }

            invoice_id = self.env['account.move'].create(invoice_vals)
            rec.invoice_id = invoice_id.id

    def action_state_refund(self):
        for rec in self:
            rec.state = 'refund'
            rec.property_id.state = 'on_sale'

    @api.onchange('property_id')
    def _onchange_property_id(self):
        for rec in self:
            if rec.property_id:
                rec.property_type = rec.property_id.property_type or ''
                rec.property_for = rec.property_id.property_for or ''

                rec.street = rec.property_id.street or ''
                rec.street2 = rec.property_id.street2 or ''
                rec.city = rec.property_id.city or ''
                rec.zip = rec.property_id.zip or ''

                rec.state_id = rec.property_id.state_id or False
                rec.country_id = rec.property_id.country_id or False

                rec.total_area = rec.property_id.total_area or 0.0
                rec.total_amount = rec.property_id.total_pricing or 0.0

                rec.landlord_id = rec.property_id.landlord_id or False

    def action_view_invoices(self):
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('invoice_origin', '=', self.name), ('move_type', '=', 'out_invoice')],
            'context': {'default_invoice_origin': self.name,
                        'default_move_type': 'out_invoice',
                        'default_partner_id': self.tenant_id.id},
        }

    @api.depends('broker_bill_id')
    def _compute_has_broker_bill(self):
        for rec in self:
            rec.has_broker_bill = bool(rec.broker_bill_id)

    def action_create_broker_bill(self):
        self.ensure_one()

        if not self.broker_id or not self.broker_commission:
            raise UserError("Please set a Broker and Commission before creating a bill.")
        if self.broker_bill_id:
            raise UserError(f"A broker bill already exists for this contract "
                            f"(Invoice: {self.broker_bill_id.name or 'N/A'}).")

        expense_account_id = self.env['account.account'].search([('account_type', '=', 'expense')], limit=1)
        if not expense_account_id:
            raise UserError("Please configure at least one expense account.")
        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.broker_id.id,
            'invoice_origin': self.name,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': fields.Date.today(),
            'currency_id': self.currency_id.id,
            'property_id': self.property_id.id,
            'sale_contract_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'name': f"Broker Commission for {self.name}",
                'quantity': 1,
                'price_unit': self.broker_commission,
                'account_id': expense_account_id.id, })], }

        bill_id = self.env['account.move'].create(bill_vals)
        self.broker_bill_id = bill_id.id

        return {
            'name': 'Broker Bill',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill_id.id,
            'view_mode': 'form',
        }

    def action_view_broker_bills(self):
        self.ensure_one()
        bill_ids = self.env['account.move'].search([
            ('property_id', '=', self.property_id.id), ('sale_contract_id', '=', self.id),
            ('move_type', '=', 'in_invoice'), ])
        return {
            'name': 'Broker Bills',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', bill_ids.ids)],
            'context': {'default_property_id': self.property_id.id,
                        'default_sale_contract_id': self.id, },
        }
