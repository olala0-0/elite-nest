from odoo import models, fields, api

RENT_INSTALLMENT_PAYMENT_TYPES = [
    ('rent', 'Rent'),
    ('deposit', 'Deposit'),
    ('maintenance', 'Maintenance'),
    ('penalty', 'Penalty'),
    ('broker_bill', 'Broker Bill'),
    ('utility', 'Utility'),
    ('dilapidation', 'Dilapidation'),
    ('shortfall_rent', 'Shortfall Rent'),
    ('ejari_fee', 'Ejari Fee'),
    ('admin_charge', 'Admin Charge'),
    ('commission', 'Commission'),
    ('parking_fee', 'Parking Fee'),
    ('management_fee', 'Management Fee'),
    ('service', 'Service / Other Charge'),
    ('other', 'Other / Manual Charge'),
]


class RentInstallment(models.Model):
    _name = 'rent.installment'
    _description = 'Rent Installment'

    rent_contract_id = fields.Many2one(
        comodel_name='rent.contract',
        string='Contract',
        check_company=False,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True,
        check_company=False,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        check_company=False,
    )
    invoice_date = fields.Date(string='Invoice Date', default=fields.Date.context_today)
    payment_type = fields.Selection(
        RENT_INSTALLMENT_PAYMENT_TYPES,
        string='Payment Type',
        default='rent',
    )
    description = fields.Char(string='Description')
    amount = fields.Monetary(string='Amount')
    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Invoice Number',
        check_company=False,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='rent_contract_id.currency_id',
        string='Currency',
        store=True,
        readonly=True,
    )
    payment_reminder_sent = fields.Boolean(string='Payment Reminder Sent', default=False, copy=False)

    def _get_valid_payment_types(self):
        selection = self._fields['payment_type'].selection
        if callable(selection):
            selection = selection(self)
        return {key for key, _label in (selection or [])}

    def _sanitize_installment_vals(self, vals):
        vals = dict(vals)
        valid_types = self._get_valid_payment_types()
        payment_type = vals.get('payment_type')
        if payment_type and payment_type not in valid_types:
            vals['payment_type'] = 'service' if 'service' in valid_types else 'other'

        # Ensure company_id aligns with product_id or target company when not explicitly provided
        product = False
        if vals.get('product_id'):
            product = self.env['product.product'].sudo().browse(vals['product_id']).exists()
            if product and product.company_id and not vals.get('company_id'):
                vals['company_id'] = product.company_id.id

        if not vals.get('company_id'):
            if vals.get('invoice_id'):
                inv = self.env['account.move'].sudo().browse(vals['invoice_id']).exists()
                if inv and inv.company_id:
                    vals['company_id'] = inv.company_id.id
            if not vals.get('company_id') and vals.get('rent_contract_id'):
                contract = self.env['rent.contract'].sudo().browse(vals['rent_contract_id']).exists()
                if contract and hasattr(contract, '_resolve_target_company'):
                    target_co = contract._resolve_target_company(
                        product=product,
                        payment_type=vals.get('payment_type', 'rent'),
                    )
                    if target_co:
                        vals['company_id'] = target_co.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        sanitized_list = [self._sanitize_installment_vals(vals) for vals in vals_list]
        return super(RentInstallment, self).create(sanitized_list)

    def write(self, vals):
        if 'payment_type' in vals:
            valid_types = self._get_valid_payment_types()
            if vals['payment_type'] and vals['payment_type'] not in valid_types:
                vals = dict(vals, payment_type='service' if 'service' in valid_types else 'other')
        return super(RentInstallment, self).write(vals)

    def _check_company(self, fnames=None):
        """Allow cross-company links between rent.installment (e.g. GHD)
        and rent.contract / property.detail (e.g. Elite Nest)."""
        if fnames is None:
            fnames = self._fields.keys()
        excluded = {'rent_contract_id', 'property_id', 'invoice_id', 'product_id', 'company_id'}
        filtered_fnames = [f for f in fnames if f not in excluded]
        return super(RentInstallment, self)._check_company(fnames=filtered_fnames)
