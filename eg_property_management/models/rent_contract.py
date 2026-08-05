import math
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round


class RentContract(models.Model):
    _name = "rent.contract"
    _description = "Rent Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Sequence', default=lambda self: 'New')

    start_date = fields.Date(string="Start Date", default=fields.Date.today)
    end_date = fields.Date(string="End Date")
    duration = fields.Integer(string="Duration (Months)", compute="_compute_duration", store=True)
    contract_days = fields.Integer(string="Contract Days", compute="_compute_contract_days", store=True)
    remaining_days = fields.Integer(string="Remaining Days", compute="_compute_remaining_days")
    payment_term_id = fields.Many2one(
        comodel_name="property.payment.term",
        string="Payment Term",
        required=True,
        default=lambda self: self.env.ref("eg_property_management.property_payment_term_monthly", raise_if_not_found=False),
    )
    payment_term = fields.Char(related="payment_term_id.name", string="Payment Term Name", store=True)
    payment_count = fields.Integer(string="Number of Payments", compute="_compute_payment_count", store=True)

    contract_type = fields.Selection(
        [('manual', 'Manual Installment'), ('auto', 'Auto Installment')],
        string="Installment Type",
        default="manual",
    )
    invoice_start_date = fields.Date(string="Invoice Start From", default=fields.Date.today)

    rent = fields.Monetary(
        string="Rent Amount",
        currency_field="currency_id",
        help="Total rent for the full contract period. Invoices are split by the number of payments.",
    )
    deposit = fields.Monetary(string="Security Deposit", currency_field="currency_id")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id)

    total_area = fields.Float(string="Total Area")
    usable_area = fields.Float(string="Usable Area")

    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    property_type = fields.Selection(
        [("land", "Land"), ("residential", "Residential"), ("commercial", "Commercial"), ("industrial", "Industrial")],
        string="Property Type", default='land')
    residential_type_id = fields.Many2one(
        comodel_name="property.residential.type",
        string="Residential Type",
        related="property_id.residential_type_id",
        store=True,
        readonly=True,
    )
    residential_type = fields.Char(related="residential_type_id.name", string="Residential Type Text", store=True)

    type = fields.Char(related="residential_type_id.name", string="Residential Type Snapshot", store=True)
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street2")
    city = fields.Char(string="City")
    state_id = fields.Many2one(comodel_name="res.country.state", string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one(comodel_name="res.country", string="Country")

    company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env.company)
    region_id = fields.Many2one(comodel_name="res.country.state", string="Region")

    tenant_id = fields.Many2one(comodel_name="res.partner", string="Tenant / Customer")
    tenant_phone = fields.Char(related="tenant_id.phone", string="Phone", readonly=True)
    tenant_email = fields.Char(related="tenant_id.email", string="Email", readonly=True)

    landlord_id = fields.Many2one(comodel_name="res.partner", string="Landlord")
    landlord_phone = fields.Char(related="landlord_id.phone", string="Phone", readonly=True)
    landlord_email = fields.Char(related="landlord_id.email", string="Email", readonly=True)

    maintenance_type = fields.Selection([('once', 'Once'), ('recurring', 'Recurring')], string="Maintenance Type",
                                        default="once")
    charge_type = fields.Selection([("fixed", "Fixed"), ("area_wise", "Area Wise")], string="Charge Type",
                                   default="fixed")
    total_maintenance = fields.Monetary(string="Maintenance", currency_field="currency_id", tracking=True)

    installment_item_id = fields.Many2one(comodel_name="product.product", string="Installment Item", )
    deposit_item_id = fields.Many2one(comodel_name="product.product", string="Deposit Item", )
    deposit_invoice_id = fields.Many2one(comodel_name='account.move', string="Deposit Invoice", readonly=True, )

    lead_id = fields.Many2one(comodel_name='crm.lead', string="Source Lead")

    penalty_type = fields.Selection([('fixed', 'Fixed'), ('percent', 'Percent')], string="Penalty Type",
                                    default='fixed')
    penalty_value = fields.Float(string="Penalty Value")
    penalty_grace_days = fields.Integer(string="Penalty Grace Days", default=3, )
    penalty_product_id = fields.Many2one(comodel_name='product.product', string='Penalty Product')

    tax_rate = fields.Float(string="Tax Rate (%)")
    taxable_amount = fields.Monetary(string="Taxable Amount", currency_field='currency_id', compute="_compute_tax",
                                     store=True)
    tax_amount = fields.Monetary(string="Tax Amount", currency_field='currency_id', compute="_compute_tax", store=True)

    user_id = fields.Many2one(comodel_name='res.users', string='Responsible User', default=lambda self: self.env.user)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")

    has_broker_bill = fields.Boolean(string="Has Broker Bill", compute="_compute_has_broker_bill", store=False)

    broker_id = fields.Many2one(comodel_name="res.partner", string="Broker / Agent",
                                domain="[('is_company','=',False)]")
    broker_phone = fields.Char(related="broker_id.phone", string="Broker Phone", readonly=True)
    broker_email = fields.Char(related="broker_id.email", string="Broker Email", readonly=True)
    broker_commission = fields.Monetary(string="Broker Commission", currency_field="currency_id", default=0.0)

    rent_installment_ids = fields.One2many(comodel_name='rent.installment', inverse_name='rent_contract_id',
                                           string="Rent Installment")

    utility_service_ids = fields.One2many(comodel_name='property.utility.service', inverse_name='rent_contract_id',
                                          string="Utility Services")
    document_ids = fields.One2many(comodel_name="property.document", inverse_name="rent_contract_id",
                                   string="Documents")
    agreement = fields.Text(string="Contract Agreement")

    terms_conditions = fields.Text(string="Terms & Conditions")

    invoice_expected_amount = fields.Monetary(string="Invoice Expected Amount", currency_field="currency_id",
                                              compute="_compute_invoice_amounts", store=True)
    invoice_paid_amount = fields.Monetary(string="Invoice Paid Amount", currency_field="currency_id",
                                          compute="_compute_invoice_amounts", store=True)
    invoice_due_amount = fields.Monetary(string="Invoice Due Amount", currency_field="currency_id",
                                         compute="_compute_invoice_due_amount")

    bill_expected_amount = fields.Monetary(string="Bill Expected Amount", currency_field="currency_id",
                                           compute="_compute_bill_amounts", store=True)
    bill_paid_amount = fields.Monetary(string="Bill Paid Amount", currency_field="currency_id",
                                       compute="_compute_bill_amounts", store=True)
    bill_due_amount = fields.Monetary(string="Bill Due Amount", currency_field="currency_id",
                                      compute="_compute_bill_due_amount")

    margin_expected = fields.Monetary(string="Margin Expected", currency_field="currency_id", compute="_compute_margin",
                                      store=True)
    margin_paid = fields.Monetary(string="Margin Paid", currency_field="currency_id", compute="_compute_margin",
                                  store=True)

    state = fields.Selection(
        [('draft', 'Draft'), ('running', 'Running'), ('cancel', 'Cancel'), ('close', 'Close'), ('expire', 'Expire'), ],
        string="Status", default='draft', tracking=True)

    invoice_count = fields.Integer(string="Invoices", compute="_compute_invoice_count")

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            seq = self.env['ir.sequence'].next_by_code('rent.contract') or '/'
            property_id = val.get('property_id')
            if property_id:
                property_rec = self.env['property.detail'].browse(property_id)
                prefix = property_rec.name or 'RC'
            else:
                prefix = 'RC'
            
            if seq.startswith('RC/'):
                val['name'] = seq.replace('RC/', f"{prefix}/")
            else:
                val['name'] = f"{prefix}/{seq}"

            if not val.get('invoice_start_date'):
                val['invoice_start_date'] = val.get('start_date') or fields.Date.today()

        return super(RentContract, self).create(vals)

    def get_tenant_financial_statement(self):
        """ Computes chronological Statement of Account data including opening balance,
        invoices, payments, running balances, totals, and security deposit details. """
        self.ensure_one()
        
        # Search posted customer invoices and credit notes linked to this contract
        invoices = self.env['account.move'].search([
            '|',
            ('rent_contract_id', '=', self.id),
            ('invoice_origin', '=', self.name),
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ], order='invoice_date asc, id asc')

        raw_lines = []

        # 1. Opening Balance entry
        raw_lines.append({
            'date': self.start_date or fields.Date.today(),
            'description': 'Opening Balance',
            'ref': '-',
            'debit': 0.0,
            'credit': 0.0,
        })

        seen_payments = set()

        for inv in invoices:
            # Invoice Line Charge (Debit / Credit)
            if inv.move_type == 'out_invoice':
                debit_val = inv.amount_total
                credit_val = 0.0
                desc = inv.invoice_line_ids[0].name if inv.invoice_line_ids else f"Rent Charge - {inv.name}"
            else:
                debit_val = 0.0
                credit_val = inv.amount_total
                desc = f"Credit Note - {inv.name}"

            raw_lines.append({
                'date': inv.invoice_date or fields.Date.today(),
                'description': desc,
                'ref': inv.name or 'Draft',
                'debit': debit_val,
                'credit': credit_val,
            })

            # Check reconciled payments against this invoice
            reconciled_payments = self.env['account.payment']
            if hasattr(inv, '_get_reconciled_payments'):
                reconciled_payments = inv._get_reconciled_payments()
            
            for payment in reconciled_payments:
                if payment.id in seen_payments:
                    continue
                seen_payments.add(payment.id)
                raw_lines.append({
                    'date': payment.date or fields.Date.today(),
                    'description': f"Payment Received ({payment.journal_id.name or 'Receipt'})",
                    'ref': payment.name or payment.ref or 'RCPT',
                    'debit': 0.0,
                    'credit': payment.amount,
                })

        # Sort all lines chronologically
        raw_lines.sort(key=lambda x: (x['date'] or fields.Date.today()))

        # Calculate running balances and totals
        running_balance = 0.0
        total_charges = 0.0
        total_payments = 0.0

        for line in raw_lines:
            running_balance += (line['debit'] - line['credit'])
            line['balance'] = running_balance
            total_charges += line['debit']
            total_payments += line['credit']

        return {
            'lines': raw_lines,
            'total_charges': total_charges,
            'total_payments': total_payments,
            'outstanding_balance': running_balance,
            'deposit_received': self.deposit or 0.0,
            'deposit_utilized': 0.0,
            'balance_held': self.deposit or 0.0,
        }

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                delta = relativedelta(rec.end_date, rec.start_date)
                total_months = (delta.years * 12) + delta.months + (delta.days / 30.0)
                rec.duration = math.ceil(total_months) if total_months > 0 else 0
            else:
                rec.duration = 0

    @api.depends('start_date', 'end_date')
    def _compute_contract_days(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date >= rec.start_date:
                rec.contract_days = (rec.end_date - rec.start_date).days + 1
            else:
                rec.contract_days = 0

    @api.depends('end_date')
    def _compute_remaining_days(self):
        today = fields.Date.today()
        for rec in self:
            if rec.end_date and rec.end_date >= today:
                rec.remaining_days = (rec.end_date - today).days
            else:
                rec.remaining_days = 0

    @api.depends('start_date', 'end_date', 'invoice_start_date', 'payment_term_id.interval_number', 'payment_term_id.interval_unit')
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = 0
            if rec.start_date and rec.end_date and rec.payment_term_id:
                current_date = rec.invoice_start_date or rec.start_date
                
                if current_date > rec.end_date:
                    rec.payment_count = 0
                    continue

                delta = rec.payment_term_id._get_relativedelta()
                count = 0
                
                while current_date <= rec.end_date:
                    count += 1
                    current_date = current_date + delta
                    if not delta:
                        break
                
                rec.payment_count = count

    @api.constrains('start_date', 'end_date')
    def _check_contract_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError("Contract end date must be after the start date.")

    @api.constrains('start_date', 'end_date', 'invoice_start_date')
    def _check_first_invoice_date(self):
        for rec in self:
            if not rec.invoice_start_date or not rec.start_date or not rec.end_date:
                continue
            if rec.invoice_start_date < rec.start_date or rec.invoice_start_date > rec.end_date:
                raise ValidationError("First invoice date must be between the contract start and end dates.")

    @api.constrains('property_id', 'state')
    def _check_running_contract_per_unit(self):
        for rec in self:
            if not rec.property_id:
                continue
            existing_contract = self.search([
                ('id', '!=', rec.id),
                ('property_id', '=', rec.property_id.id),
                ('state', '=', 'running'),
            ], limit=1)
            if existing_contract:
                raise UserError(
                    f"Unit '{rec.property_id.display_name}' already has an active running contract "
                    f"('{existing_contract.name}'). Please close, cancel, or expire it before creating "
                    f"or starting another contract for this unit."
                )

    def _get_invoice_settings(self):
        self.ensure_one()
        param_obj = self.env['ir.config_parameter'].sudo()
        product_obj = self.env['product.product'].sudo()

        def _get_product(key, fallback=False):
            product_id = param_obj.get_param(key)
            if product_id and str(product_id).isdigit():
                product = product_obj.browse(int(product_id)).exists()
                if product:
                    return product
            return fallback

        return {
            'rent_product': _get_product(
                'eg_property_management.rent_invoice_product_id',
                self.installment_item_id,
            ),
            'rent_description': param_obj.get_param(
                'eg_property_management.rent_invoice_description',
                'Rent Installment',
            ),
            'deposit_product': _get_product(
                'eg_property_management.deposit_invoice_product_id',
                self.deposit_item_id,
            ),
            'deposit_description': param_obj.get_param(
                'eg_property_management.deposit_invoice_description',
                'Security Deposit',
            ),
            'maintenance_product': _get_product('eg_property_management.maintenance_invoice_product_id'),
            'maintenance_description': param_obj.get_param(
                'eg_property_management.maintenance_invoice_description',
                'Maintenance Charge',
            ),
            'penalty_product': _get_product(
                'eg_property_management.penalty_invoice_product_id',
                self.penalty_product_id,
            ),
            'penalty_description': param_obj.get_param(
                'eg_property_management.penalty_invoice_description',
                'Penalty',
            ),
        }

    def _get_next_rent_invoice_date(self):
        self.ensure_one()
        rent_installments = self.rent_installment_ids.filtered(lambda inst: inst.payment_type == 'rent')
        last_installment = rent_installments.sorted('invoice_date')[-1:] if rent_installments else self.env['rent.installment']
        next_due_date = self.invoice_start_date or self.start_date
        if last_installment:
            next_due_date = last_installment.invoice_date + self.payment_term_id._get_relativedelta()
        return next_due_date, last_installment

    def _get_total_contract_rent(self):
        self.ensure_one()
        precision = self.currency_id.rounding or 0.01
        return float_round(self.rent or 0.0, precision_rounding=precision)

    def _get_rent_schedule_dates(self):
        self.ensure_one()
        if not self.start_date or not self.end_date or not self.payment_term_id:
            return []

        due_dates = []
        current_date = self.invoice_start_date or self.start_date
        delta = self.payment_term_id._get_relativedelta()
        while current_date and current_date < self.end_date:
            due_dates.append(current_date)
            current_date = current_date + delta

        if not due_dates and current_date == self.end_date:
            due_dates.append(current_date)
        return due_dates

    def _get_pending_rent_due_dates(self):
        self.ensure_one()
        existing_due_dates = set(
            self.rent_installment_ids.filtered(lambda inst: inst.payment_type == 'rent').mapped('invoice_date')
        )
        return [due_date for due_date in self._get_rent_schedule_dates() if due_date not in existing_due_dates]

    def _get_pending_rent_amount_map(self, pending_due_dates=None):
        self.ensure_one()
        pending_due_dates = pending_due_dates or self._get_pending_rent_due_dates()
        if not pending_due_dates:
            return {}

        existing_rent_installments = self.rent_installment_ids.filtered(lambda inst: inst.payment_type == 'rent')
        remaining_amount = self._get_total_contract_rent() - sum(existing_rent_installments.mapped('amount'))
        precision = self.currency_id.rounding or 0.01
        remaining_count = len(pending_due_dates)
        amount_map = {}

        for due_date in pending_due_dates:
            if remaining_count == 1:
                installment_amount = float_round(remaining_amount, precision_rounding=precision)
            else:
                installment_amount = float_round(remaining_amount / remaining_count, precision_rounding=precision)
            amount_map[due_date] = installment_amount
            remaining_amount -= installment_amount
            remaining_count -= 1
        return amount_map

    def _get_maintenance_charge_amount(self):
        self.ensure_one()
        maint_amount = self.total_maintenance
        if self.charge_type == 'area_wise':
            maint_amount *= (self.total_area or 0.0)
        return maint_amount

    @staticmethod
    def _prepare_invoice_line(product, description, amount, account_id):
        return (0, 0, {
            'product_id': product.id if product else False,
            'name': description,
            'quantity': 1,
            'price_unit': amount,
            'account_id': account_id.id,
        })

    def _get_next_rent_amount(self):
        self.ensure_one()
        pending_due_dates = self._get_pending_rent_due_dates()
        if not pending_due_dates:
            return 0.0
        amount_map = self._get_pending_rent_amount_map(pending_due_dates)
        return amount_map.get(pending_due_dates[0], 0.0)

    def action_state_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_state_running(self):
        for rec in self:
            rec.state = 'running'
            rec.property_id.state = 'rent'

    def action_state_close(self):
        for rec in self:
            rec.state = 'close'
            rec.property_id.state = 'on_rent'

    def action_state_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            rec.property_id.state = 'on_rent'

    def action_expire(self):
        for rec in self:
            rec.state = 'expire'
            rec.property_id.state = 'on_rent'

    def action_create_invoice(self):
        self.ensure_one()
        if not self.tenant_id:
            raise UserError("Please set a Tenant/Customer on the contract before creating an invoice.")
        if not self.start_date or not self.end_date:
            raise UserError("Please set contract Start Date and End Date.")
        if not self.payment_term_id:
            raise UserError("Please set a payment term on the contract.")
        income_account_id = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
        if not income_account_id:
            raise UserError("No income account found. Please configure at least one income account in Accounting.")

        invoice_settings = self._get_invoice_settings()
        existing_installments = self.rent_installment_ids
        pending_due_dates = self._get_pending_rent_due_dates()
        if not pending_due_dates:
            raise UserError("All invoices based on the payment count have already been created for this contract.")

        due_dates_to_invoice = pending_due_dates if self.contract_type == 'auto' else pending_due_dates[:1]
        rent_amount_map = self._get_pending_rent_amount_map(pending_due_dates)
        first_batch_due_date = due_dates_to_invoice[0] if due_dates_to_invoice else False
        invoice_ids = self.env['account.move']

        for due_date in due_dates_to_invoice:
            invoice_lines = []
            installments = []
            deposit_added = False

            rent_amount = rent_amount_map.get(due_date, 0.0)
            if due_date <= self.end_date and rent_amount:
                invoice_lines.append(
                    self._prepare_invoice_line(
                        invoice_settings['rent_product'],
                        invoice_settings['rent_description'],
                        rent_amount,
                        income_account_id,
                    )
                )
                installments.append({
                    'rent_contract_id': self.id,
                    'invoice_date': due_date,
                    'payment_type': 'rent',
                    'description': invoice_settings['rent_description'],
                    'amount': rent_amount,
                    'currency_id': self.currency_id.id,
                })

            if due_date == first_batch_due_date and self.deposit and self.deposit > 0 and not self.deposit_invoice_id:
                invoice_lines.append(
                    self._prepare_invoice_line(
                        invoice_settings['deposit_product'],
                        invoice_settings['deposit_description'],
                        self.deposit,
                        income_account_id,
                    )
                )
                installments.append({
                    'rent_contract_id': self.id,
                    'invoice_date': self.start_date,
                    'payment_type': 'deposit',
                    'description': invoice_settings['deposit_description'],
                    'amount': self.deposit,
                    'currency_id': self.currency_id.id,
                })
                deposit_added = True

            maint_amount = self._get_maintenance_charge_amount()
            if maint_amount > 0:
                if self.maintenance_type == 'once':
                    already_exists_id = existing_installments.filtered(
                        lambda inst: inst.payment_type == 'maintenance'
                        and inst.description == invoice_settings['maintenance_description']
                    )[:1]
                    if due_date == first_batch_due_date and not already_exists_id:
                        invoice_lines.append(
                            self._prepare_invoice_line(
                                invoice_settings['maintenance_product'],
                                invoice_settings['maintenance_description'],
                                maint_amount,
                                income_account_id,
                            )
                        )
                        installments.append({
                            'rent_contract_id': self.id,
                            'invoice_date': self.start_date,
                            'payment_type': 'maintenance',
                            'description': invoice_settings['maintenance_description'],
                            'amount': maint_amount,
                            'currency_id': self.currency_id.id,
                        })
                elif self.maintenance_type == 'recurring':
                    already_exists_id = existing_installments.filtered(
                        lambda inst: inst.payment_type == 'maintenance'
                        and inst.invoice_date == due_date
                        and inst.description == invoice_settings['maintenance_description']
                    )[:1]
                    if not already_exists_id:
                        invoice_lines.append(
                            self._prepare_invoice_line(
                                invoice_settings['maintenance_product'],
                                invoice_settings['maintenance_description'],
                                maint_amount,
                                income_account_id,
                            )
                        )
                        installments.append({
                            'rent_contract_id': self.id,
                            'invoice_date': due_date,
                            'payment_type': 'maintenance',
                            'description': invoice_settings['maintenance_description'],
                            'amount': maint_amount,
                            'currency_id': self.currency_id.id,
                        })

            for service_id in self.utility_service_ids:
                if service_id.service_type == 'once':
                    utility_description = f"{service_id.service_id.name} (One-time)"
                    already_exists_id = existing_installments.filtered(
                        lambda inst: inst.payment_type == 'utility' and inst.description == utility_description
                    )[:1]
                    if due_date == first_batch_due_date and not already_exists_id:
                        invoice_lines.append(
                            self._prepare_invoice_line(
                                service_id.service_id,
                                utility_description,
                                service_id.cost,
                                income_account_id,
                            )
                        )
                        installments.append({
                            'rent_contract_id': self.id,
                            'invoice_date': self.start_date,
                            'payment_type': 'utility',
                            'description': utility_description,
                            'amount': service_id.cost,
                            'currency_id': self.currency_id.id,
                        })
                elif service_id.service_type == 'recurring':
                    utility_description = f"{service_id.service_id.name} for {due_date}"
                    already_exists_id = existing_installments.filtered(
                        lambda inst: inst.payment_type == 'utility'
                        and inst.invoice_date == due_date
                        and inst.description == utility_description
                    )[:1]
                    if not already_exists_id:
                        invoice_lines.append(
                            self._prepare_invoice_line(
                                service_id.service_id,
                                utility_description,
                                service_id.cost,
                                income_account_id,
                            )
                        )
                        installments.append({
                            'rent_contract_id': self.id,
                            'invoice_date': due_date,
                            'payment_type': 'utility',
                            'description': utility_description,
                            'amount': service_id.cost,
                            'currency_id': self.currency_id.id,
                        })

            if not invoice_lines:
                continue

            invoice_id = self.env['account.move'].with_context(skip_sync_installment=True).create({
                'move_type': 'out_invoice',
                'partner_id': self.tenant_id.id,
                'invoice_origin': self.name,
                'invoice_date': due_date,
                'invoice_date_due': due_date,
                'currency_id': self.currency_id.id,
                'property_id': self.property_id.id,
                'rent_contract_id': self.id,
                'invoice_line_ids': invoice_lines,
            })

            for inst in installments:
                inst['invoice_id'] = invoice_id.id
                self.env['rent.installment'].create(inst)

            if deposit_added and not self.deposit_invoice_id:
                self.deposit_invoice_id = invoice_id.id
            invoice_ids |= invoice_id

        if not invoice_ids:
            raise UserError("Nothing to invoice for this period.")

        if len(invoice_ids) == 1:
            return {
                'name': 'Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoice_ids.id,
                'view_mode': 'form',
            }

        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoice_ids.ids)],
        }

    @api.depends('rent_installment_ids.amount', 'rent_installment_ids.payment_type',
                 'rent_installment_ids.invoice_id.state', 'rent_installment_ids.invoice_id.amount_total')
    def _compute_invoice_amounts(self):
        for record in self:
            rent_installments_id = record.rent_installment_ids.filtered(lambda r: r.payment_type != 'broker_bill')
            record.invoice_expected_amount = sum(rent_installments_id.mapped('amount'))
            unique_invoices_id = rent_installments_id.mapped('invoice_id').filtered(lambda inv: inv.state == 'posted')
            record.invoice_paid_amount = sum(unique_invoices_id.mapped('amount_total'))

    @api.depends('rent_installment_ids', 'rent_installment_ids.invoice_id.state')
    def _compute_bill_amounts(self):
        for record in self:
            broker_installments_ids = record.rent_installment_ids.filtered(
                lambda inst: inst.payment_type == 'broker_bill' and inst.invoice_id)

            record.bill_expected_amount = sum(broker_installments_ids.mapped('amount'))
            record.bill_paid_amount = sum(
                inst.invoice_id.amount_total
                for inst in broker_installments_ids
                if inst.invoice_id.state == 'posted')

    @api.depends('invoice_expected_amount', 'invoice_paid_amount')
    def _compute_invoice_due_amount(self):
        for record in self:
            record.invoice_due_amount = record.invoice_expected_amount - record.invoice_paid_amount

    @api.depends('bill_expected_amount', 'bill_paid_amount')
    def _compute_bill_due_amount(self):
        for record in self:
            record.bill_due_amount = record.bill_expected_amount - record.bill_paid_amount

    @api.depends('invoice_expected_amount', 'bill_expected_amount', 'invoice_paid_amount', 'bill_paid_amount')
    def _compute_margin(self):
        for record in self:
            record.margin_expected = record.invoice_expected_amount - record.bill_expected_amount
            record.margin_paid = record.invoice_paid_amount - record.bill_paid_amount

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': 'Customer Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                '|',
                ('rent_contract_id', '=', self.id),
                ('invoice_origin', '=', self.name)
            ],
        }

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = self.env['account.move'].search_count([
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                '|',
                ('rent_contract_id', '=', rec.id),
                ('invoice_origin', '=', rec.name)
            ])

    @api.onchange('property_id')
    def _onchange_property_id(self):
        for rec in self:
            if rec.property_id:
                rec.property_type = rec.property_id.property_type or ''
                rec.street = rec.property_id.street or ''
                rec.street2 = rec.property_id.street2 or ''
                rec.city = rec.property_id.city or ''
                rec.zip = rec.property_id.zip or ''
                rec.state_id = rec.property_id.state_id or False
                rec.country_id = rec.property_id.country_id or False
                rec.total_area = rec.property_id.total_area or 0.0
                rec.usable_area = rec.property_id.usable_area or 0.0
                rec.landlord_id = rec.property_id.landlord_id or False

                rec.rent = rec.property_id.rent_amount or 0.0
                rec.deposit = rec.property_id.sale_amount or 0.0
                rec.maintenance_type = rec.property_id.maintenance_type or 'once'
                rec.charge_type = rec.property_id.charge_type or 'fixed'
                rec.total_maintenance = rec.property_id.total_maintenance or 0.0

                rec.utility_service_ids = [(5, 0, 0)]
                service_lines = []
                for service_id in rec.property_id.utility_service_ids:
                    service_lines.append((0, 0, {
                        'service_id': service_id.service_id.id,
                        'service_type': service_id.service_type,
                        'cost': service_id.cost,
                        'currency_id': service_id.currency_id.id,
                    }))
                rec.utility_service_ids = service_lines

    @api.onchange('start_date')
    def _onchange_start_date(self):
        for rec in self:
            if rec.start_date and (not rec.invoice_start_date or rec.invoice_start_date < rec.start_date):
                rec.invoice_start_date = rec.start_date

    def action_create_broker_bill(self):
        self.ensure_one()
        if not self.broker_id or not self.broker_commission:
            raise UserError("Please set a Broker and Commission before creating a bill.")

        existing_broker_inst_id = self.env['rent.installment'].search(
            [('rent_contract_id', '=', self.id), ('payment_type', '=', 'broker_bill'), ], limit=1)

        if existing_broker_inst_id:
            raise UserError(f"A broker bill already exists for this contract "
                            f"(Invoice: {existing_broker_inst_id.invoice_id.name or 'N/A'}).")

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
            'rent_contract_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'name': f"Broker Commission for {self.name}",
                'quantity': 1,
                'price_unit': self.broker_commission,
                'account_id': expense_account_id.id,
            })],
        }
        bill_id = self.env['account.move'].create(bill_vals)

        self.env['rent.installment'].create({
            'rent_contract_id': self.id,
            'invoice_date': fields.Date.today(),
            'payment_type': 'broker_bill',
            'description': f"Broker Bill for {self.name}",
            'amount': self.broker_commission,
            'invoice_id': bill_id.id,
            'currency_id': self.currency_id.id,
        })
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
            ('property_id', '=', self.property_id.id), ('rent_contract_id', '=', self.id),
            ('move_type', '=', 'in_invoice'), ])
        return {
            'name': 'Broker Bills',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', bill_ids.ids)],
            'context': {'default_property_id': self.property_id.id,
                        'default_rent_contract_id': self.id, },
        }

    @api.depends('rent', 'total_maintenance', 'utility_service_ids.cost', 'tax_rate')
    def _compute_tax(self):
        for rec in self:
            base = rec.rent or 0.0
            base += rec.total_maintenance or 0.0
            base += sum(rec.utility_service_ids.mapped('cost'))
            rec.taxable_amount = base
            rec.tax_amount = (base * rec.tax_rate / 100.0) if rec.tax_rate else 0.0

    def action_apply_penalty_cron(self):
        today = date.today()
        overdue_installments_ids = self.env['rent.installment'].search([
            ('payment_type', '=', 'rent'), ('invoice_id.payment_state', '!=', 'paid'),
            ('invoice_id.invoice_date', '<', today - timedelta(days=1)), ])

        for installments_id in overdue_installments_ids:
            contract_id = installments_id.rent_contract_id

            if not contract_id.penalty_value:
                continue

            if (today - installments_id.invoice_date).days <= contract_id.penalty_grace_days:
                continue

            if self.env['rent.installment'].search_count([
                ('rent_contract_id', '=', contract_id.id), ('payment_type', '=', 'penalty'),
                ('invoice_id.invoice_origin', '=', installments_id.invoice_id.name)]) > 0:
                continue

            penalty_amount = contract_id.penalty_value
            if contract_id.penalty_type == 'percent':
                penalty_amount = (installments_id.amount or 0.0) * (contract_id.penalty_value or 0.0) / 100.0

            income_account_id = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
            if not income_account_id:
                continue

            invoice_settings = contract_id._get_invoice_settings()
            move_vals = {
                'move_type': 'out_invoice',
                'partner_id': contract_id.tenant_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
                'currency_id': contract_id.currency_id.id,
                'invoice_origin': contract_id.name,
                'property_id': contract_id.property_id.id,
                'rent_contract_id': contract_id.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': invoice_settings['penalty_product'].id if invoice_settings['penalty_product'] else False,
                    'name': invoice_settings['penalty_description'],
                    'quantity': 1,
                    'price_unit': penalty_amount,
                    'account_id': income_account_id.id,
                })],
            }
            invoice_id = self.env['account.move'].with_context(skip_sync_installment=True).create(move_vals)

            self.env['rent.installment'].create({
                'rent_contract_id': contract_id.id,
                'invoice_date': fields.Date.today(),
                'payment_type': 'penalty',
                'description': invoice_settings['penalty_description'],
                'amount': penalty_amount,
                'invoice_id': invoice_id.id,
                'currency_id': contract_id.currency_id.id, })
            contract_id.message_post(
                body=f"Penalty invoice {invoice_id.name} generated for overdue installment {installments_id.id}.")

    def action_rent_due_reminder_cron(self):
        today = date.today()
        reminder_days = 7
        upcoming_installment_ids = self.env['rent.installment'].search([
            ('invoice_date', '=', today - timedelta(days=reminder_days)), ('invoice_id', '!=', False),
            ('invoice_id.payment_state', '!=', 'paid'), ('rent_contract_id.state', '=', 'running'), ])
        for installment_id in upcoming_installment_ids:
            contract_id = installment_id.rent_contract_id
            contract_id.message_post(
                body=f"Reminder: Rent installment of {installment_id.amount} is due on {installment_id.invoice_date}."
            )
            if contract_id.tenant_id.email:
                mail_values = {
                    'subject': f"Rent Due Reminder - {contract_id.name}",
                    'body_html': f"""
                        <p>Dear {contract_id.tenant_id.name},</p>
                        <p>This is a reminder that your rent installment of 
                        <b>{installment_id.amount} {contract_id.currency_id.symbol}</b> 
                        is due on <b>{installment_id.invoice_date}</b>.</p>
                        <p>Regards,<br/>{contract_id.company_id.name}</p>
                    """,
                    'email_to': contract_id.tenant_id.email, }
                self.env['mail.mail'].create(mail_values).send()

    def action_contract_expiry_cron(self):
        today = date.today()
        expired_contracts_ids = self.search([('end_date', '<', today), ('state', '=', 'running')])
        for expired_contracts_id in expired_contracts_ids:
            expired_contracts_id.state = 'expire'
            expired_contracts_id.property_id.state = 'on_rent'
            expired_contracts_id.message_post(
                body=f"This contract reached its end date on <b>{expired_contracts_id.end_date}</b> "
                     f"and has been automatically moved to the status <b>Expired</b>.")
        return True

    def action_auto_create_invoice_cron(self):
        today = fields.Date.today()
        contract_ids = self.search(
            [('state', '=', 'running'), ('contract_type', '=', 'auto'), ('start_date', '<=', today),
             ('end_date', '>=', today), ])

        for contract_id in contract_ids:
            next_due_date, _last_installment_id = contract_id._get_next_rent_invoice_date()

            if today < next_due_date:
                continue
            try:
                contract_id.action_create_invoice()
            except UserError:
                continue

    @api.depends('rent_installment_ids.payment_type')
    def _compute_has_broker_bill(self):
        for rec in self:
            rec.has_broker_bill = any(inst.payment_type == 'broker_bill' for inst in rec.rent_installment_ids)
