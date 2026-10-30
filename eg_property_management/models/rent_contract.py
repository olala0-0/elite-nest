import math
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round

# account.move.payment_state values, spelled out for the printed statement -
# the raw selection values ("in_payment", "not_paid") aren't fit to show a
# tenant directly.
PAYMENT_STATE_LABELS = {
    'not_paid': 'Not Paid',
    'in_payment': 'In Payment',
    'paid': 'Paid',
    'partial': 'Partially Paid',
    'reversed': 'Reversed',
}

# (contract field name, display label) for the four one-time charges shown
# in the tenant statement's Security Deposit box - field name doubles as
# the matching rent.installment.payment_type (see rent_installment.py).
ONE_TIME_CHARGE_FIELDS = [
    ('ejari_fee', 'Ejari Fee'),
    ('admin_charge', 'Admin Charge'),
    ('commission', 'Commission'),
    ('parking_fee', 'Parking Fee'),
]


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
    dewa_premises_no = fields.Char(
        related="property_id.x_studio_dewa_premises_no",
        string="DEWA Premises No.",
        store=True,
        readonly=True,
    )

    property_id = fields.Many2one(comodel_name="property.detail", string="Property", check_company=False)
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

    tenant_id = fields.Many2one(comodel_name="res.partner", string="Tenant / Customer", check_company=False)
    tenant_phone = fields.Char(related="tenant_id.phone", string="Phone", readonly=True)
    tenant_email = fields.Char(related="tenant_id.email", string="Email", readonly=True)
    tenant_country_id = fields.Many2one(
        comodel_name="res.country",
        related="tenant_id.country_id",
        string="Customer Country",
        store=True,
        readonly=False,
    )

    landlord_id = fields.Many2one(comodel_name="res.partner", string="Landlord", check_company=False)
    landlord_phone = fields.Char(related="landlord_id.phone", string="Phone", readonly=True)
    landlord_email = fields.Char(related="landlord_id.email", string="Email", readonly=True)

    maintenance_type = fields.Selection([('once', 'Once'), ('recurring', 'Recurring')], string="Maintenance Type",
                                        default="once")
    charge_type = fields.Selection([("fixed", "Fixed"), ("area_wise", "Area Wise")], string="Charge Type",
                                   default="fixed")
    total_maintenance = fields.Monetary(string="Maintenance", currency_field="currency_id", tracking=True)

    installment_item_id = fields.Many2one(comodel_name="product.product", string="Installment Item", check_company=False)
    deposit_item_id = fields.Many2one(comodel_name="product.product", string="Deposit Item", check_company=False)
    deposit_invoice_id = fields.Many2one(comodel_name='account.move', string="Deposit Invoice", readonly=True, check_company=False)

    # One-time charges (Ejari Fee / Admin Charge / Commission / Parking Fee) -
    # each follows the exact Security Deposit pattern above: a configured
    # amount, an optional per-contract product override, and a readonly
    # invoice-reference field that both prevents billing it twice and lets
    # other logic (reports, statements) find which invoice carried it.
    ejari_fee = fields.Monetary(string="Ejari Fee", currency_field="currency_id")
    ejari_fee_item_id = fields.Many2one(comodel_name="product.product", string="Ejari Fee Item", check_company=False)
    ejari_fee_invoice_id = fields.Many2one(comodel_name='account.move', string="Ejari Fee Invoice", readonly=True, check_company=False)

    admin_charge = fields.Monetary(string="Admin Charge", currency_field="currency_id")
    admin_charge_item_id = fields.Many2one(comodel_name="product.product", string="Admin Charge Item", check_company=False)
    admin_charge_invoice_id = fields.Many2one(comodel_name='account.move', string="Admin Charge Invoice", readonly=True, check_company=False)

    commission = fields.Monetary(
        string="Commission", currency_field="currency_id",
        help="Tenant-facing commission charge, billed once like the Security "
             "Deposit. Not related to Broker Commission (broker_commission), "
             "which is a separate vendor bill paid out to the broker.")
    commission_item_id = fields.Many2one(comodel_name="product.product", string="Commission Item", check_company=False)
    commission_invoice_id = fields.Many2one(comodel_name='account.move', string="Commission Invoice", readonly=True, check_company=False)

    parking_fee = fields.Monetary(string="Parking Fee", currency_field="currency_id")
    parking_fee_item_id = fields.Many2one(comodel_name="product.product", string="Parking Fee Item", check_company=False)
    parking_fee_invoice_id = fields.Many2one(comodel_name='account.move', string="Parking Fee Invoice", readonly=True, check_company=False)

    lead_id = fields.Many2one(comodel_name='crm.lead', string="Source Lead")

    penalty_type = fields.Selection([('fixed', 'Fixed'), ('percent', 'Percent')], string="Penalty Type",
                                    default='fixed')
    penalty_value = fields.Float(string="Penalty Value")
    penalty_grace_days = fields.Integer(string="Penalty Grace Days", default=3)
    penalty_product_id = fields.Many2one(comodel_name='product.product', string='Penalty Product', check_company=False)

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

    # Status terminology updated to past-tense conventions
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('running', 'Running'),
            ('move_out', 'Move-Out Process'),
            ('cancelled', 'Cancelled'),
            ('terminated', 'Terminated'),
            ('expired', 'Expired'),
        ],
        string="Status", default='draft', tracking=True
    )

    invoice_count = fields.Integer(string="Invoices", compute="_compute_invoice_count")
    expiry_notified_90_days = fields.Boolean(string="Expiry 90-Days Notified", default=False, copy=False)

    def _check_company(self, fnames=None):
        if fnames is None:
            fnames = self._fields.keys()
        excluded = {
            'property_id', 'tenant_id', 'landlord_id', 'broker_id', 'lead_id',
            'installment_item_id', 'deposit_item_id', 'deposit_invoice_id',
            'ejari_fee_item_id', 'ejari_fee_invoice_id',
            'admin_charge_item_id', 'admin_charge_invoice_id',
            'commission_item_id', 'commission_invoice_id',
            'parking_fee_item_id', 'parking_fee_invoice_id',
            'penalty_product_id', 'movein_id', 'moveout_id',
        }
        filtered_fnames = [f for f in fnames if f not in excluded]
        return super(RentContract, self)._check_company(fnames=filtered_fnames)
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

    def write(self, vals):
        if 'end_date' in vals:
            vals['expiry_notified_90_days'] = False
        return super(RentContract, self).write(vals)

    def _invoice_status_label(self, invoice):
        """Human-readable status for one charge's invoice, for the printed
        statement - distinguishes "never invoiced" from "invoiced but still
        draft" from the actual payment_state once posted."""
        if not invoice:
            return 'Not Invoiced'
        if invoice.state == 'cancel':
            return 'Cancelled'
        if invoice.state != 'posted':
            return 'Draft - Not Confirmed'
        return PAYMENT_STATE_LABELS.get(
            invoice.payment_state, (invoice.payment_state or 'not_paid').replace('_', ' ').title()
        )

    def _get_invoice_paid_amount(self, invoice):
        """Authoritative amount actually paid on one invoice: amount_total
        minus amount_residual - the same core fields Odoo itself uses to
        compute payment_state, so it's correct no matter how the payment
        was reconciled (a registered payment, a bank statement match, a
        write-off, ...)."""
        self.ensure_one()
        return invoice.amount_total - invoice.amount_residual

    def _get_invoice_payment_matches(self, invoice):
        """Best-effort per-payment breakdown (name/date/reference) for
        display only - NOT the source of truth for how much was paid, see
        _get_invoice_paid_amount() for that."""
        receivable_lines = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
        )
        matches = []
        for partial in receivable_lines.matched_debit_ids:
            counterpart = partial.credit_move_id
            if counterpart.payment_id:
                matches.append((counterpart.payment_id, partial.amount, counterpart.payment_id.date))
        for partial in receivable_lines.matched_credit_ids:
            counterpart = partial.debit_move_id
            if counterpart.payment_id:
                matches.append((counterpart.payment_id, partial.amount, counterpart.payment_id.date))
        return matches

    def _get_deposit_summary(self):
        """Single source of truth for what's actually been invoiced/paid
        for the security deposit - reflects real invoice state, not just
        the amount configured on the contract."""
        self.ensure_one()
        deposit_installment = self.rent_installment_ids.filtered(
            lambda inst: inst.payment_type == 'deposit'
        )[:1]
        deposit_invoice = deposit_installment.invoice_id if deposit_installment else self.env['account.move']
        deposit_status = (
            self._invoice_status_label(deposit_invoice) if deposit_installment else 'Not Yet Invoiced'
        )
        deposit_received = (
            deposit_installment.amount
            if deposit_installment and deposit_invoice and deposit_invoice.state == 'posted'
            else 0.0
        )

        moveout = self.env['rent.contract.moveout'].search(
            [('rent_contract_id', '=', self.id)], limit=1
        )
        deposit_utilized = 0.0
        if moveout and moveout.deduction_invoice_id and moveout.deduction_invoice_id.state == 'posted':
            deposit_utilized = min(moveout.deduction_invoice_id.amount_total, deposit_received)

        return {
            'deposit_installment': deposit_installment,
            'deposit_invoice': deposit_invoice,
            'deposit_status': deposit_status,
            'deposit_received': deposit_received,
            'deposit_utilized': deposit_utilized,
            'moveout': moveout,
        }

    def _get_one_time_charges_summary(self):
        """Amount Due / Status for each of the four one-time contract
        charges (Ejari Fee, Admin Charge, Commission, Parking Fee) that
        actually have a value set."""
        self.ensure_one()
        summary = []
        for field_name, label in ONE_TIME_CHARGE_FIELDS:
            amount = self[field_name]
            if not amount:
                continue
            installment = self.rent_installment_ids.filtered(
                lambda inst, pt=field_name: inst.payment_type == pt
            )[:1]
            invoice = installment.invoice_id if installment else self.env['account.move']
            status = self._invoice_status_label(invoice) if installment else 'Not Yet Invoiced'
            summary.append({'label': label, 'amount': amount, 'status': status})
        return summary

    def get_tenant_financial_statement(self):
        """Computes chronological Statement of Account data including opening balance,
        one row per charge (rent/deposit/maintenance/utility/penalty), matched payments,
        running balances, totals, payment counts, and security deposit status."""
        self.ensure_one()

        raw_lines = [{
            'date': self.start_date or fields.Date.today(),
            'description': 'Opening Balance',
            'ref': '-',
            'status': '-',
            'debit': 0.0,
            'credit': 0.0,
            'pending': False,
            'company': self.company_id.name,
        }]

        charge_installments = self.rent_installment_ids.filtered(
            lambda inst: inst.payment_type != 'broker_bill'
        ).sorted(key=lambda inst: (inst.invoice_date or fields.Date.today(), inst.id))

        confirmed_count = 0
        pending_count = 0
        total_pending_amount = 0.0
        posted_invoices = self.env['account.move']

        for inst in charge_installments:
            invoice = inst.invoice_id
            status = self._invoice_status_label(invoice)
            is_posted = bool(invoice and invoice.state == 'posted')

            if not is_posted:
                pending_amount = self._amount_with_tax(invoice, inst.amount)
                pending_count += 1
                total_pending_amount += pending_amount
                raw_lines.append({
                    'date': inst.invoice_date,
                    'description': f"{inst.description or inst.payment_type.title()} (not yet confirmed)",
                    'ref': invoice.name if invoice and invoice.name and invoice.name != '/' else 'Draft',
                    'status': status,
                    'debit': pending_amount,
                    'credit': 0.0,
                    'pending': True,
                    'company': invoice.company_id.name if invoice else self.company_id.name,
                })
                continue

            confirmed_count += 1
            posted_invoices |= invoice
            raw_lines.append({
                'date': invoice.invoice_date or inst.invoice_date,
                'description': inst.description or invoice.name,
                'ref': invoice.name,
                'status': status,
                'debit': self._amount_with_tax(invoice, inst.amount),
                'credit': 0.0,
                'pending': False,
                'company': invoice.company_id.name,
            })

        for invoice in posted_invoices:
            paid_amount = self._get_invoice_paid_amount(invoice)
            if paid_amount <= 0.005:
                continue

            matches = self._get_invoice_payment_matches(invoice)
            matched_total = sum(m[1] for m in matches)

            if matches and abs(matched_total - paid_amount) <= 0.01:
                for payment, matched_amount, pay_date in matches:
                    raw_lines.append({
                        'date': pay_date or invoice.invoice_date or fields.Date.today(),
                        'description': f"Payment Received ({payment.journal_id.name or 'Receipt'})",
                        'ref': payment.name or payment.ref or 'RCPT',
                        'status': 'Paid',
                        'debit': 0.0,
                        'credit': matched_amount,
                        'pending': False,
                        'company': payment.company_id.name or invoice.company_id.name,
                    })
            else:
                raw_lines.append({
                    'date': invoice.invoice_date_due or invoice.invoice_date or fields.Date.today(),
                    'description': f"Payment Received (matched to {invoice.name})",
                    'ref': invoice.name,
                    'status': 'Paid',
                    'debit': 0.0,
                    'credit': paid_amount,
                    'pending': False,
                    'company': invoice.company_id.name,
                })

        refunds = self.env['account.move'].search([
            '|',
            ('rent_contract_id', '=', self.id),
            ('invoice_origin', '=', self.name),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_refund'),
        ], order='invoice_date asc, id asc')
        for refund in refunds:
            raw_lines.append({
                'date': refund.invoice_date or fields.Date.today(),
                'description': f"Credit Note - {refund.name}",
                'ref': refund.name,
                'status': 'Posted',
                'debit': 0.0,
                'credit': refund.amount_total,
                'pending': False,
                'company': refund.company_id.name,
            })

        raw_lines.sort(key=lambda x: (x['date'] or fields.Date.today()))

        running_balance = 0.0
        total_charges = 0.0
        total_payments = 0.0

        for line in raw_lines:
            if line['pending']:
                line['balance'] = running_balance
                continue
            running_balance += (line['debit'] - line['credit'])
            line['balance'] = running_balance
            total_charges += line['debit']
            total_payments += line['credit']

        deposit_summary = self._get_deposit_summary()
        deposit_status = deposit_summary['deposit_status']
        deposit_received = deposit_summary['deposit_received']
        deposit_utilized = deposit_summary['deposit_utilized']
        one_time_charges = self._get_one_time_charges_summary()

        deduction_lines = []
        deposit_refund_amount = 0.0
        moveout = deposit_summary['moveout']
        if moveout and moveout.deduction_invoice_id and moveout.deduction_invoice_id.state == 'posted':
            for line in moveout.deduction_line_ids:
                deduction_lines.append({
                    'category': dict(line._fields['charge_category'].selection).get(line.charge_category),
                    'description': line.description,
                    'amount': line.amount,
                })
            if moveout.refund_move_id and moveout.refund_move_id.state == 'posted':
                deposit_refund_amount = moveout.refund_move_id.amount_total

        return {
            'lines': raw_lines,
            'total_charges': total_charges,
            'total_payments': total_payments,
            'outstanding_balance': running_balance,
            'payment_count': self.payment_count,
            'confirmed_count': confirmed_count,
            'pending_count': pending_count,
            'total_pending_amount': total_pending_amount,
            'deposit_configured': self.deposit or 0.0,
            'deposit_status': deposit_status,
            'deposit_received': deposit_received,
            'deposit_utilized': deposit_utilized,
            'balance_held': deposit_received - deposit_utilized,
            'one_time_charges': one_time_charges,
            'deduction_lines': deduction_lines,
            'deposit_refund_amount': deposit_refund_amount,
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
                ('state', 'in', ('running', 'move_out')),
            ], limit=1)
            if existing_contract:
                raise UserError(
                    f"Unit '{rec.property_id.display_name}' already has an active running contract "
                    f"('{existing_contract.name}'). Please terminate, cancel, or expire it before creating "
                    f"or starting another contract for this unit."
                )

    def _get_ghd_company(self):
        """Find the GHD company used for Rent Installments and Security Deposits."""
        return self.env['res.company'].sudo().search([('name', 'ilike', 'GHD')], limit=1)

    def _get_contract_company(self):
        """Return the contract or property management company (e.g. Elite Nest)."""
        self.ensure_one()
        return self.company_id or self.property_id.sudo().company_id or self.env.company

    def _resolve_target_company(self, product=False, payment_type='service'):
        """Dynamically resolve target company for an installment / invoice line:
        1. From the Product (product.company_id) if set.
        2. By Charge Type fallback (if product.company_id is empty):
           - 'rent' and 'deposit' -> GHD company.
           - All other services / one-time charges -> Contract / Property company.
        """
        self.ensure_one()
        is_product = bool(product and getattr(product, '_name', '') in ('product.product', 'product.template'))
        if is_product:
            prod_company = product.sudo().company_id
            if prod_company:
                return prod_company
        if payment_type in ('rent', 'deposit'):
            ghd_company = self._get_ghd_company()
            if ghd_company:
                return ghd_company
        return self._get_contract_company()

    def _resolve_service_product(self, utility_line):
        """Resolve an optional product.product for a property.utility.service line
        so future utility/service charges can inherit a product's company_id and income account."""
        if not utility_line:
            return self.env['product.product']
        for candidate in (getattr(utility_line, 'product_id', False), getattr(utility_line.service_id, 'product_id', False), utility_line.service_id):
            if candidate and getattr(candidate, '_name', '') == 'product.product':
                return candidate.sudo()
        if utility_line.service_id and utility_line.service_id.name:
            matched = self.env['product.product'].sudo().search([
                ('name', '=ilike', utility_line.service_id.name.strip())
            ], limit=1)
            if matched:
                return matched
        return self.env['product.product']

    def _get_company_sale_journal(self, target_company, payment_type='service'):
        """Select the Sales Journal belonging to target_company."""
        journal_obj = self.env['account.journal'].with_company(target_company).sudo()
        if payment_type in ('rent', 'deposit'):
            rent_journal = journal_obj.search([
                ('type', '=', 'sale'),
                ('company_id', '=', target_company.id),
                ('name', 'ilike', 'rent'),
            ], limit=1)
            if rent_journal:
                return rent_journal
        journal = journal_obj.search([
            ('type', '=', 'sale'),
            ('company_id', '=', target_company.id),
        ], limit=1)
        if not journal:
            raise UserError(f"No Sales Journal found for company '{target_company.display_name}'.")
        return journal

    def _get_company_income_account(self, product, target_company, journal=False):
        """Resolve the income account in target_company context:
        1. product.with_company(target_company).property_account_income_id
        2. product.with_company(target_company).categ_id.property_account_income_categ_id
        3. journal.default_account_id
        4. Fallback income account in target_company
        """
        is_product = bool(product and getattr(product, '_name', '') in ('product.product', 'product.template'))
        if is_product:
            prod_ctx = product.with_company(target_company).sudo()
            account = (
                prod_ctx.property_account_income_id
                or prod_ctx.categ_id.with_company(target_company).property_account_income_categ_id
            )
            if account:
                return account
        if journal and journal.sudo().default_account_id:
            return journal.sudo().default_account_id
        account_obj = self.env['account.account'].with_company(target_company).sudo()
        domain = [('account_type', 'in', ('income', 'income_other'))]
        if 'company_ids' in account_obj._fields:
            domain.append(('company_ids', 'in', target_company.ids))
        elif 'company_id' in account_obj._fields:
            domain.append(('company_id', '=', target_company.id))
        account = account_obj.search(domain, limit=1)
        if not account:
            raise UserError(
                f"No income account found for company '{target_company.display_name}'. "
                f"Please configure an income account in Accounting."
            )
        return account

    def _get_invoice_settings(self):
        self.ensure_one()
        param_obj = self.env['ir.config_parameter'].sudo()
        contract_company = self._get_contract_company()
        ghd_company = self._get_ghd_company() or contract_company

        def _get_product(key, fallback=False, default_company=None, name_fallback=None):
            ctx_company = default_company or contract_company
            product_obj = self.env['product.product'].with_company(ctx_company).sudo()
            product = self.env['product.product']
            product_id = param_obj.get_param(key)
            if product_id and str(product_id).isdigit():
                product = product_obj.browse(int(product_id)).exists()
            if not product and fallback:
                product = fallback.sudo().exists()
            if not product and name_fallback:
                product = product_obj.search([('name', 'ilike', name_fallback)], limit=1)
            if product:
                resolved_company = product.sudo().company_id or ctx_company
                return product.with_company(resolved_company).sudo()
            return fallback

        return {
            'rent_product': _get_product(
                'eg_property_management.rent_invoice_product_id',
                self.sudo().installment_item_id,
                default_company=ghd_company,
                name_fallback='Installment Property Payment',
            ),
            'rent_description': param_obj.get_param(
                'eg_property_management.rent_invoice_description',
                'Rent Installment',
            ),
            'deposit_product': _get_product(
                'eg_property_management.deposit_invoice_product_id',
                self.sudo().deposit_item_id,
                default_company=ghd_company,
            ),
            'deposit_description': param_obj.get_param(
                'eg_property_management.deposit_invoice_description',
                'Security Deposit',
            ),
            'maintenance_product': _get_product(
                'eg_property_management.maintenance_invoice_product_id',
                default_company=contract_company,
            ),
            'maintenance_description': param_obj.get_param(
                'eg_property_management.maintenance_invoice_description',
                'Maintenance Charge',
            ),
            'penalty_product': _get_product(
                'eg_property_management.penalty_invoice_product_id',
                self.sudo().penalty_product_id,
                default_company=contract_company,
            ),
            'penalty_description': param_obj.get_param(
                'eg_property_management.penalty_invoice_description',
                'Penalty',
            ),
            'ejari_fee_product': _get_product(
                'eg_property_management.ejari_fee_invoice_product_id',
                self.sudo().ejari_fee_item_id,
                default_company=contract_company,
            ),
            'ejari_fee_description': param_obj.get_param(
                'eg_property_management.ejari_fee_invoice_description',
                'Ejari Fee',
            ),
            'admin_charge_product': _get_product(
                'eg_property_management.admin_charge_invoice_product_id',
                self.sudo().admin_charge_item_id,
                default_company=contract_company,
            ),
            'admin_charge_description': param_obj.get_param(
                'eg_property_management.admin_charge_invoice_description',
                'Admin Charge',
            ),
            'commission_product': _get_product(
                'eg_property_management.commission_invoice_product_id',
                self.sudo().commission_item_id,
                default_company=contract_company,
            ),
            'commission_description': param_obj.get_param(
                'eg_property_management.commission_invoice_description',
                'Commission',
            ),
            'parking_fee_product': _get_product(
                'eg_property_management.parking_fee_invoice_product_id',
                self.sudo().parking_fee_item_id,
                default_company=contract_company,
            ),
            'parking_fee_description': param_obj.get_param(
                'eg_property_management.parking_fee_invoice_description',
                'Parking Fee',
            ),
            'dilapidation_product': _get_product(
                'eg_property_management.dilapidation_invoice_product_id',
                default_company=contract_company,
            ),
            'dilapidation_description': param_obj.get_param(
                'eg_property_management.dilapidation_invoice_description',
                'Dilapidation',
            ),
            'shortfall_rent_product': _get_product(
                'eg_property_management.shortfall_rent_invoice_product_id',
                default_company=contract_company,
            ),
            'shortfall_rent_description': param_obj.get_param(
                'eg_property_management.shortfall_rent_invoice_description',
                'Shortfall Rent',
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
    def _amount_with_tax(invoice, base_amount):
        if not invoice or not invoice.amount_untaxed:
            return base_amount
        return base_amount * (invoice.amount_total / invoice.amount_untaxed)

    @staticmethod
    def _prepare_invoice_line(product, description, amount, account_id=False, target_company=False, journal=False):
        is_product = bool(product and getattr(product, '_name', '') == 'product.product')
        prod_ctx = product.with_company(target_company).sudo() if (is_product and target_company) else (product.sudo() if is_product else False)
        resolved_account = False
        if prod_ctx:
            categ_ctx = prod_ctx.categ_id.with_company(target_company) if target_company else prod_ctx.categ_id
            resolved_account = prod_ctx.property_account_income_id or categ_ctx.property_account_income_categ_id
        if not resolved_account and journal and journal.sudo().default_account_id:
            resolved_account = journal.sudo().default_account_id
        if not resolved_account:
            resolved_account = account_id

        line_vals = {
            'product_id': prod_ctx.id if prod_ctx else False,
            'name': description,
            'quantity': 1,
            'price_unit': amount,
        }
        if resolved_account:
            line_vals['account_id'] = resolved_account.id
        if prod_ctx and target_company:
            taxes = prod_ctx.taxes_id.filtered(lambda t: not t.company_id or t.company_id == target_company)
            line_vals['tax_ids'] = [(6, 0, taxes.ids)]
        return (0, 0, line_vals)

    def _get_next_rent_amount(self):
        self.ensure_one()
        pending_due_dates = self._get_pending_rent_due_dates()
        if not pending_due_dates:
            return 0.0
        amount_map = self._get_pending_rent_amount_map(pending_due_dates)
        return amount_map.get(pending_due_dates[0], 0.0)

    def _get_finance_users(self):
        """Find users representing the Finance / Accounting team."""
        # 1. Configured finance users in Settings
        config_user_ids = self.env['ir.config_parameter'].sudo().get_param('eg_property_management.finance_user_ids')
        if config_user_ids:
            try:
                user_ids = [int(u_id.strip()) for u_id in config_user_ids.split(',') if u_id.strip().isdigit()]
                users = self.env['res.users'].browse(user_ids).exists().filtered(lambda u: u.active)
                if users:
                    return users
            except Exception:
                pass

        groups_field = 'group_ids' if 'group_ids' in self.env['res.users']._fields else 'groups_id'

        # 2. Users belonging to standard Odoo Accounting / Invoicing groups
        groups = [
            'account.group_account_invoice',
            'account.group_account_user',
            'account.group_account_manager',
        ]
        group_ids = []
        for group_xml_id in groups:
            group = self.env.ref(group_xml_id, raise_if_not_found=False)
            if group:
                group_ids.append(group.id)

        users = self.env['res.users']
        if group_ids:
            users = self.env['res.users'].search([
                (groups_field, 'in', group_ids),
                ('share', '=', False),
                ('active', '=', True),
            ])

        if not users:
            admin_group = self.env.ref('base.group_erp_manager', raise_if_not_found=False)
            if admin_group:
                users = self.env['res.users'].search([
                    (groups_field, 'in', admin_group.ids),
                    ('share', '=', False),
                    ('active', '=', True),
                ])
        return users

    def _get_finance_partners(self):
        """Find partners associated with Finance users to receive in-system notifications."""
        finance_users = self._get_finance_users()
        return finance_users.mapped('partner_id')

    def _send_system_notification(self, title, message, partners, activity_summary=None, activity_user_ids=None):
        """Send in-system notification directly to partners and users:
        1. Posts in contract chatter with forced notification_type='in_app'
           (increments Discuss systray unread badge, no emails sent even if database neutralized).
        2. Sends real-time pop-up notification via bus.bus to connected users.
        3. Optionally schedules mail.activity for users.
        """
        self.ensure_one()
        if not partners:
            return

        # 1. Post notification in contract chatter
        msg = self.message_post(
            body=f"<b>{title}</b><br/>{message}",
            subject=title,
            partner_ids=partners.ids,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
        # Force notification delivery to inbox (Discuss inbox) instead of email
        if msg and msg.notification_ids:
            try:
                msg.notification_ids.sudo().write({'notification_type': 'inbox'})
            except Exception:
                pass

        # 2. Real-time pop-up notification via bus.bus (requires clean plain text)
        plain_message = message
        try:
            from odoo.tools import html2plaintext
            plain_message = html2plaintext(message).strip()
        except Exception:
            pass
        if '<' in plain_message and '>' in plain_message:
            import re
            plain_message = re.sub(r'<br\s*/?>', '\n', plain_message, flags=re.IGNORECASE)
            plain_message = re.sub(r'<[^>]+>', '', plain_message).strip()

        plain_title = title
        if '<' in plain_title and '>' in plain_title:
            import re
            plain_title = re.sub(r'<[^>]+>', '', plain_title).strip()

        for partner in partners:
            try:
                self.env['bus.bus']._sendone(
                    partner,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': plain_title,
                        'message': plain_message,
                        'sticky': False,
                    }
                )
            except Exception:
                try:
                    self.env['bus.bus']._sendone(
                        partner,
                        'mail.simple_notification',
                        {
                            'type': 'info',
                            'title': plain_title,
                            'message': plain_message,
                            'sticky': False,
                        }
                    )
                except Exception:
                    pass

        # 3. Schedule mail.activity if requested
        if activity_summary and activity_user_ids:
            for user in activity_user_ids:
                existing_activity = self.env['mail.activity'].search([
                    ('res_model', '=', self._name),
                    ('res_id', '=', self.id),
                    ('user_id', '=', user.id),
                    ('summary', '=', activity_summary),
                ], limit=1)
                if not existing_activity:
                    try:
                        self.activity_schedule(
                            'mail.mail_activity_data_todo',
                            user_id=user.id,
                            summary=activity_summary,
                            note=message,
                        )
                    except Exception:
                        pass

    def action_state_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_state_running(self):
        for rec in self:
            rec.state = 'running'
            rec.property_id.state = 'on_rent'

    def action_state_terminate(self):
        for rec in self:
            rec.state = 'terminated'
            if rec.property_id:
                rec.property_id.write({'state': 'available'})

    def action_state_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            if rec.property_id:
                rec.property_id.write({'state': 'available'})

    def action_expire(self):
        for rec in self:
            rec.state = 'expired'
            if rec.property_id:
                rec.property_id.write({'state': 'available'})

    def action_create_invoice(self):
        self.ensure_one()
        if not self.tenant_id:
            raise UserError("Please set a Tenant/Customer on the contract before creating an invoice.")
        if not self.start_date or not self.end_date:
            raise UserError("Please set contract Start Date and End Date.")
        if not self.payment_term_id:
            raise UserError("Please set a payment term on the contract.")

        invoice_settings = self._get_invoice_settings()
        existing_installments = self.sudo().rent_installment_ids
        pending_due_dates = self._get_pending_rent_due_dates()
        if not pending_due_dates:
            raise UserError("All invoices based on the payment count have already been created for this contract.")

        due_dates_to_invoice = pending_due_dates if self.contract_type == 'auto' else pending_due_dates[:1]
        rent_amount_map = self._get_pending_rent_amount_map(pending_due_dates)
        first_batch_due_date = due_dates_to_invoice[0] if due_dates_to_invoice else False
        invoice_ids = self.env['account.move'].sudo()

        for due_date in due_dates_to_invoice:
            charge_items = []

            def _add_charge(product, description, amount, payment_type, inst_date, contract_invoice_field=None):
                target_co = self._resolve_target_company(product=product, payment_type=payment_type)
                charge_items.append({
                    'product': product,
                    'description': description,
                    'amount': amount,
                    'payment_type': payment_type,
                    'installment_date': inst_date,
                    'target_company': target_co,
                    'contract_invoice_field': contract_invoice_field,
                })

            rent_amount = rent_amount_map.get(due_date, 0.0)
            if due_date <= self.end_date and rent_amount:
                _add_charge(
                    invoice_settings['rent_product'],
                    invoice_settings['rent_description'],
                    rent_amount,
                    'rent',
                    due_date,
                )

            if due_date == first_batch_due_date and self.deposit and self.deposit > 0 and not self.deposit_invoice_id:
                _add_charge(
                    invoice_settings['deposit_product'],
                    invoice_settings['deposit_description'],
                    self.deposit,
                    'deposit',
                    self.start_date,
                    contract_invoice_field='deposit_invoice_id',
                )

            if due_date == first_batch_due_date and self.ejari_fee and self.ejari_fee > 0 and not self.ejari_fee_invoice_id:
                _add_charge(
                    invoice_settings['ejari_fee_product'],
                    invoice_settings['ejari_fee_description'],
                    self.ejari_fee,
                    'ejari_fee',
                    self.start_date,
                    contract_invoice_field='ejari_fee_invoice_id',
                )

            if due_date == first_batch_due_date and self.admin_charge and self.admin_charge > 0 and not self.admin_charge_invoice_id:
                _add_charge(
                    invoice_settings['admin_charge_product'],
                    invoice_settings['admin_charge_description'],
                    self.admin_charge,
                    'admin_charge',
                    self.start_date,
                    contract_invoice_field='admin_charge_invoice_id',
                )

            if due_date == first_batch_due_date and self.commission and self.commission > 0 and not self.commission_invoice_id:
                _add_charge(
                    invoice_settings['commission_product'],
                    invoice_settings['commission_description'],
                    self.commission,
                    'commission',
                    self.start_date,
                    contract_invoice_field='commission_invoice_id',
                )

            if due_date == first_batch_due_date and self.parking_fee and self.parking_fee > 0 and not self.parking_fee_invoice_id:
                _add_charge(
                    invoice_settings['parking_fee_product'],
                    invoice_settings['parking_fee_description'],
                    self.parking_fee,
                    'parking_fee',
                    self.start_date,
                    contract_invoice_field='parking_fee_invoice_id',
                )

            maint_amount = self._get_maintenance_charge_amount()
            if maint_amount > 0:
                if self.maintenance_type == 'once':
                    already_exists_id = existing_installments.filtered(
                        lambda inst: inst.payment_type == 'maintenance'
                        and inst.description == invoice_settings['maintenance_description']
                    )[:1]
                    if due_date == first_batch_due_date and not already_exists_id:
                        _add_charge(
                            invoice_settings['maintenance_product'],
                            invoice_settings['maintenance_description'],
                            maint_amount,
                            'maintenance',
                            self.start_date,
                        )
                elif self.maintenance_type == 'recurring':
                    already_exists_id = existing_installments.filtered(
                        lambda inst: inst.payment_type == 'maintenance'
                        and inst.invoice_date == due_date
                        and inst.description == invoice_settings['maintenance_description']
                    )[:1]
                    if not already_exists_id:
                        _add_charge(
                            invoice_settings['maintenance_product'],
                            invoice_settings['maintenance_description'],
                            maint_amount,
                            'maintenance',
                            due_date,
                        )

            for service_id in self.utility_service_ids:
                service_product = self._resolve_service_product(service_id)
                if service_id.service_type == 'once':
                    utility_description = f"{service_id.service_id.name} (One-time)"
                    already_exists_id = existing_installments.filtered(
                        lambda inst: inst.payment_type in ('utility', 'service')
                        and inst.description == utility_description
                    )[:1]
                    if due_date == first_batch_due_date and not already_exists_id:
                        _add_charge(
                            service_product,
                            utility_description,
                            service_id.cost,
                            'utility',
                            self.start_date,
                        )
                elif service_id.service_type == 'recurring':
                    utility_description = f"{service_id.service_id.name} for {due_date}"
                    already_exists_id = existing_installments.filtered(
                        lambda inst: inst.payment_type in ('utility', 'service')
                        and inst.invoice_date == due_date
                        and inst.description == utility_description
                    )[:1]
                    if not already_exists_id:
                        _add_charge(
                            service_product,
                            utility_description,
                            service_id.cost,
                            'utility',
                            due_date,
                        )

            if not charge_items:
                continue

            # Group charge items by target_company so lines from different companies
            # (e.g. GHD Rent/Deposit vs Elite Nest Admin/Ejari/Maintenance) never mix in one account.move
            batches_by_company = {}
            company_order = []
            for item in charge_items:
                co = item['target_company']
                if co.id not in batches_by_company:
                    batches_by_company[co.id] = []
                    company_order.append(co)
                batches_by_company[co.id].append(item)

            for target_company in company_order:
                batch_items = batches_by_company[target_company.id]
                primary_type = (
                    'rent'
                    if any(it['payment_type'] in ('rent', 'deposit') for it in batch_items)
                    else batch_items[0]['payment_type']
                )
                journal = self._get_company_sale_journal(target_company, payment_type=primary_type)
                invoice_lines = []
                for item in batch_items:
                    line_account = self._get_company_income_account(
                        item['product'],
                        target_company,
                        journal=journal,
                    )
                    invoice_lines.append(
                        self._prepare_invoice_line(
                            item['product'],
                            item['description'],
                            item['amount'],
                            line_account,
                            target_company=target_company,
                            journal=journal,
                        )
                    )

                move_env = self.env['account.move'].with_company(target_company).sudo().with_context(
                    skip_sync_installment=True,
                    default_company_id=target_company.id,
                    allowed_company_ids=target_company.ids,
                )
                invoice_id = move_env.create({
                    'move_type': 'out_invoice',
                    'company_id': target_company.id,
                    'journal_id': journal.id,
                    'partner_id': self.tenant_id.id,
                    'invoice_origin': self.name,
                    'invoice_date': due_date,
                    'invoice_date_due': due_date,
                    'currency_id': self.currency_id.id,
                    'property_id': self.property_id.id,
                    'rent_contract_id': self.id,
                    'invoice_line_ids': invoice_lines,
                })

                inst_env = self.env['rent.installment'].with_company(target_company).sudo()
                for item in batch_items:
                    is_prod = bool(item['product'] and getattr(item['product'], '_name', '') == 'product.product')
                    new_inst = inst_env.create({
                        'rent_contract_id': self.id,
                        'company_id': target_company.id,
                        'product_id': item['product'].id if is_prod else False,
                        'invoice_date': item['installment_date'],
                        'payment_type': item['payment_type'],
                        'description': item['description'],
                        'amount': item['amount'],
                        'currency_id': self.currency_id.id,
                        'invoice_id': invoice_id.id,
                    })
                    existing_installments |= new_inst
                    inv_field = item.get('contract_invoice_field')
                    if inv_field and inv_field in self._fields and not self[inv_field]:
                        self.sudo().write({inv_field: invoice_id.id})

                invoice_ids |= invoice_id

        if not invoice_ids:
            raise UserError("Nothing to invoice for this period.")

        allowed_companies = (self.env.companies | invoice_ids.mapped('company_id')).ids
        if len(invoice_ids) == 1:
            return {
                'name': 'Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoice_ids.id,
                'view_mode': 'form',
                'context': {'allowed_company_ids': allowed_companies},
            }

        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoice_ids.ids)],
            'context': {'allowed_company_ids': allowed_companies},
        }

    @api.depends('rent_installment_ids.amount', 'rent_installment_ids.payment_type',
                 'rent_installment_ids.invoice_id.state', 'rent_installment_ids.invoice_id.amount_total')
    def _compute_invoice_amounts(self):
        for record in self:
            rent_installments_id = record.sudo().rent_installment_ids.filtered(lambda r: r.payment_type != 'broker_bill')
            record.invoice_expected_amount = sum(rent_installments_id.mapped('amount'))
            unique_invoices_id = rent_installments_id.mapped('invoice_id').filtered(lambda inv: inv.state == 'posted')
            record.invoice_paid_amount = sum(unique_invoices_id.mapped('amount_total'))

    @api.depends('rent_installment_ids', 'rent_installment_ids.invoice_id.state')
    def _compute_bill_amounts(self):
        for record in self:
            broker_installments_ids = record.sudo().rent_installment_ids.filtered(
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
        linked_invoices = self.env['account.move'].sudo().search([
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            '|',
            ('rent_contract_id', '=', self.id),
            ('invoice_origin', '=', self.name),
        ])
        allowed_companies = (self.env.companies | linked_invoices.mapped('company_id')).ids
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
            'context': {'allowed_company_ids': allowed_companies},
        }

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = self.env['account.move'].sudo().search_count([
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

        existing_broker_inst_id = self.env['rent.installment'].sudo().search(
            [('rent_contract_id', '=', self.id), ('payment_type', '=', 'broker_bill'), ], limit=1)

        if existing_broker_inst_id:
            raise UserError(f"A broker bill already exists for this contract "
                            f"(Invoice: {existing_broker_inst_id.invoice_id.name or 'N/A'}).")

        target_company = self._get_contract_company()
        account_obj = self.env['account.account'].with_company(target_company).sudo()
        domain = [('account_type', '=', 'expense')]
        if 'company_ids' in account_obj._fields:
            domain.append(('company_ids', 'in', target_company.ids))
        elif 'company_id' in account_obj._fields:
            domain.append(('company_id', '=', target_company.id))
        expense_account_id = account_obj.search(domain, limit=1)
        if not expense_account_id:
            raise UserError("Please configure at least one expense account.")

        bill_vals = {
            'move_type': 'in_invoice',
            'company_id': target_company.id,
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
        bill_id = self.env['account.move'].with_company(target_company).sudo().create(bill_vals)

        self.env['rent.installment'].with_company(target_company).sudo().create({
            'rent_contract_id': self.id,
            'company_id': target_company.id,
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
        bill_ids = self.env['account.move'].sudo().search([
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
        overdue_installments_ids = self.env['rent.installment'].sudo().search([
            ('payment_type', '=', 'rent'), ('invoice_id.payment_state', '!=', 'paid'),
            ('invoice_id.invoice_date', '<', today - timedelta(days=1)), ])

        for installments_id in overdue_installments_ids:
            contract_id = installments_id.rent_contract_id

            if not contract_id.penalty_value:
                continue

            if (today - installments_id.invoice_date).days <= contract_id.penalty_grace_days:
                continue

            if self.env['rent.installment'].sudo().search_count([
                ('rent_contract_id', '=', contract_id.id), ('payment_type', '=', 'penalty'),
                ('invoice_id.invoice_origin', '=', installments_id.invoice_id.name)]) > 0:
                continue

            penalty_amount = contract_id.penalty_value
            if contract_id.penalty_type == 'percent':
                penalty_amount = (installments_id.amount or 0.0) * (contract_id.penalty_value or 0.0) / 100.0

            invoice_settings = contract_id._get_invoice_settings()
            penalty_product = invoice_settings['penalty_product']
            target_company = contract_id._resolve_target_company(
                product=penalty_product,
                payment_type='penalty',
            )
            try:
                journal = contract_id._get_company_sale_journal(target_company, payment_type='penalty')
                income_account_id = contract_id._get_company_income_account(
                    penalty_product,
                    target_company,
                    journal=journal,
                )
            except UserError:
                continue

            move_vals = {
                'move_type': 'out_invoice',
                'company_id': target_company.id,
                'journal_id': journal.id,
                'partner_id': contract_id.tenant_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
                'currency_id': contract_id.currency_id.id,
                'invoice_origin': contract_id.name,
                'property_id': contract_id.property_id.id,
                'rent_contract_id': contract_id.id,
                'invoice_line_ids': [
                    contract_id._prepare_invoice_line(
                        penalty_product,
                        invoice_settings['penalty_description'],
                        penalty_amount,
                        income_account_id,
                        target_company=target_company,
                        journal=journal,
                    )
                ],
            }
            invoice_id = self.env['account.move'].with_company(target_company).sudo().with_context(
                skip_sync_installment=True,
                default_company_id=target_company.id,
                allowed_company_ids=target_company.ids,
            ).create(move_vals)

            is_prod = bool(penalty_product and getattr(penalty_product, '_name', '') == 'product.product')
            self.env['rent.installment'].with_company(target_company).sudo().create({
                'rent_contract_id': contract_id.id,
                'company_id': target_company.id,
                'product_id': penalty_product.id if is_prod else False,
                'invoice_date': fields.Date.today(),
                'payment_type': 'penalty',
                'description': invoice_settings['penalty_description'],
                'amount': penalty_amount,
                'invoice_id': invoice_id.id,
                'currency_id': contract_id.currency_id.id,
            })
            contract_id.message_post(
                body=f"Penalty invoice {invoice_id.name} generated for overdue installment {installments_id.id}.")

    def action_rent_due_reminder_cron(self):
        """Send tenant payment reminders 10 to 15 days before the scheduled payment date:
        - Sends pop-up notification and Discuss inbox message to Finance team and contract responsible user.
        - Sends email reminder to Tenant if email exists.
        - Schedules activity for responsible user.
        """
        today = date.today()
        min_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'eg_property_management.payment_reminder_min_days', '10'))
        max_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'eg_property_management.payment_reminder_max_days', '15'))

        window_start = today + timedelta(days=min_days)
        window_end = today + timedelta(days=max_days)

        upcoming_installment_ids = self.env['rent.installment'].search([
            ('invoice_date', '>=', window_start),
            ('invoice_date', '<=', window_end),
            ('payment_reminder_sent', '=', False),
            ('rent_contract_id.state', 'in', ('running', 'move_out')),
        ])
        for installment_id in upcoming_installment_ids:
            # Skip if invoice exists and is already paid
            if installment_id.invoice_id and installment_id.invoice_id.payment_state in ('paid', 'in_payment'):
                continue

            installment_id.payment_reminder_sent = True
            contract_id = installment_id.rent_contract_id
            days_until_due = (installment_id.invoice_date - today).days

            title = f"Tenant Payment Reminder: {contract_id.name}"
            msg_body = (
                f"Reminder: Rent installment of <b>{installment_id.amount} {contract_id.currency_id.symbol or ''}</b> "
                f"is scheduled for <b>{installment_id.invoice_date}</b> ({days_until_due} day(s) from today) "
                f"for contract <b>{contract_id.name}</b> (Tenant: <b>{contract_id.tenant_id.name or 'N/A'}</b>)."
            )

            # In-system notification directly to Finance team and contract responsible user
            recipients = contract_id._get_finance_partners()
            if contract_id.user_id and contract_id.user_id.partner_id:
                recipients |= contract_id.user_id.partner_id

            contract_id._send_system_notification(
                title=title,
                message=msg_body,
                partners=recipients,
                activity_summary=f"Payment Reminder: Due in {days_until_due} days",
                activity_user_ids=contract_id.user_id or contract_id._get_finance_users(),
            )

            # Email notification to Tenant
            if contract_id.tenant_id.email:
                mail_values = {
                    'subject': f"Rent Due Reminder - {contract_id.name}",
                    'body_html': f"""
                        <p>Dear {contract_id.tenant_id.name},</p>
                        <p>This is a reminder that your rent installment of 
                        <b>{installment_id.amount} {contract_id.currency_id.symbol}</b> 
                        is scheduled for payment on <b>{installment_id.invoice_date}</b> ({days_until_due} day(s) from today).</p>
                        <p>Property: <b>{contract_id.property_id.name or 'Your Property'}</b></p>
                        <p>Regards,<br/>{contract_id.company_id.name}</p>
                    """,
                    'email_to': contract_id.tenant_id.email,
                }
                try:
                    self.env['mail.mail'].create(mail_values).send()
                except Exception:
                    pass
        return True

    def action_renewal_notice_cron(self):
        """Move-Out diagram step 1: send the renewal notice N calendar
        months before a running contract's end date, N chosen by the agent
        in Settings (eg_property_management.renewal_notice_months, 1/2/3,
        default 3). Only touches 'running' contracts, so anything already
        terminated, cancelled, or expired is never matched."""
        notice_months = int(self.env['ir.config_parameter'].sudo().get_param(
            'eg_property_management.renewal_notice_months', '3'
        ))
        today = date.today()
        target_date = today + relativedelta(months=notice_months)
        contracts = self.search([
            ('state', '=', 'running'),
            ('end_date', '=', target_date),
        ])
        for contract in contracts:
            contract.message_post(
                body=f"Renewal notice: this contract's end date ({contract.end_date}) is now "
                     f"{notice_months} month(s) away."
            )
            if contract.tenant_id.email:
                mail_values = {
                    'subject': f"Lease Renewal Notice - {contract.name}",
                    'body_html': f"""
                        <p>Dear {contract.tenant_id.name},</p>
                        <p>Your lease for <b>{contract.property_id.name or 'your property'}</b> is due to
                        expire on <b>{contract.end_date}</b> ({notice_months} month(s) from today).</p>
                        <p>Please let us know whether you'd like to renew or plan to move out, so we can
                        prepare the next steps with you accordingly.</p>
                        <p>Regards,<br/>{contract.company_id.name}</p>
                    """,
                    'email_to': contract.tenant_id.email,
                }
                self.env['mail.mail'].create(mail_values).send()
        return True

    def action_contract_expiry_cron(self):
        """1. Move expired contracts past end_date to 'expire'.
        2. Trigger contract expiry notifications exactly 90 days before the contract expiry date:
           - In-system pop-up and Discuss notification for Finance team and responsible user.
           - Activity scheduled on the contract.
        """
        today = date.today()
        # 1. Handle contracts that have already expired
        expired_contracts_ids = self.search([('end_date', '<', today), ('state', '=', 'running')])
        for expired_contracts_id in expired_contracts_ids:
            expired_contracts_id.state = 'expired'
            expired_contracts_id.property_id.state = 'available'
            expired_contracts_id.message_post(
                body=f"This contract reached its end date on <b>{expired_contracts_id.end_date}</b> "
                     f"and has been automatically moved to the status <b>Expired</b>.")

        # 2. Contract expiry notification triggered 90 days before end_date
        expiry_notice_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'eg_property_management.contract_expiry_notice_days', '90'))
        target_expiry_date = today + timedelta(days=expiry_notice_days)

        expiring_contracts_ids = self.search([
            ('state', '=', 'running'),
            ('end_date', '<=', target_expiry_date),
            ('end_date', '>=', today),
            ('expiry_notified_90_days', '=', False),
        ])
        for contract in expiring_contracts_ids:
            contract.expiry_notified_90_days = True
            days_left = (contract.end_date - today).days if contract.end_date else expiry_notice_days
            title = f"Contract Expiry Notice: {contract.name} expires in {days_left} days"
            message = (
                f"Tenancy Contract <b>{contract.name}</b> for property <b>{contract.property_id.name or 'N/A'}</b> "
                f"(Tenant: <b>{contract.tenant_id.name or 'N/A'}</b>) is scheduled to expire on "
                f"<b>{contract.end_date}</b> ({days_left} day(s) from today). "
                f"Please review renewal or move-out arrangements."
            )

            recipients = contract._get_finance_partners()
            if contract.user_id and contract.user_id.partner_id:
                recipients |= contract.user_id.partner_id

            contract._send_system_notification(
                title=title,
                message=message,
                partners=recipients,
                activity_summary=f"Contract Expiry in {days_left} Days",
                activity_user_ids=contract.user_id or contract._get_finance_users(),
            )
        return True

    def action_auto_create_invoice_cron(self):
        today = fields.Date.today()
        contract_ids = self.search(
            [('state', 'in', ('running', 'move_out')), ('contract_type', '=', 'auto'), ('start_date', '<=', today),
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

    movein_id = fields.Many2one(comodel_name='rent.contract.movein', string='Move-In Record',
                                compute='_compute_movein_id')

    def _compute_movein_id(self):
        for rec in self:
            rec.movein_id = self.env['rent.contract.movein'].search(
                [('rent_contract_id', '=', rec.id)], limit=1
            )

    def action_open_movein(self):
        """Smart-button target: opens the contract's Move-In record,
        creating it on first click."""
        self.ensure_one()
        movein = self.movein_id
        if not movein:
            movein = self.env['rent.contract.movein'].create({'rent_contract_id': self.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rent.contract.movein',
            'res_id': movein.id,
            'view_mode': 'form',
            'target': 'current',
        }

    moveout_id = fields.Many2one(comodel_name='rent.contract.moveout', string='Move-Out Record',
                                 compute='_compute_moveout_id')
    moveout_state = fields.Selection(
        [('draft', 'Move-Out: Draft'), ('clearance_pending', 'Move-Out: Clearance Pending'),
         ('inspection_done', 'Move-Out: Final Inspection'), ('finance_review', 'Move-Out: Finance Review'),
         ('approved', 'Move-Out: Approved'), ('settled', 'Move-Out: Settled')],
        string='Move-Out Status', compute='_compute_moveout_state')

    def _compute_moveout_state(self):
        for rec in self:
            rec.moveout_state = rec.moveout_id.state

    def _compute_moveout_id(self):
        for rec in self:
            rec.moveout_id = self.env['rent.contract.moveout'].search(
                [('rent_contract_id', '=', rec.id)], limit=1
            )

    def action_start_moveout(self):
        """Header-button target for 'Start Move-Out Process'. Creates the
        Move-Out record and moves the contract's own state to 'move_out'."""
        self.ensure_one()
        if self.state != 'running':
            raise UserError("Only a running contract can start the Move-Out process.")
        if not self.moveout_id:
            self.env['rent.contract.moveout'].create({'rent_contract_id': self.id})
        self.state = 'move_out'

    def action_open_moveout(self):
        """Smart-button target: opens the contract's existing Move-Out record."""
        self.ensure_one()
        moveout = self.moveout_id
        if not moveout:
            if self.state not in ('running', 'move_out'):
                raise UserError("Only a running contract can start the Move-Out process.")
            moveout = self.env['rent.contract.moveout'].create({'rent_contract_id': self.id})
            if self.state == 'running':
                self.state = 'move_out'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rent.contract.moveout',
            'res_id': moveout.id,
            'view_mode': 'form',
            'target': 'current',
        }
