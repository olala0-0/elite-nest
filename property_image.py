from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError


class RentContract(models.Model):
    _name = "rent.contract"
    _description = "Rent Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Sequence', default=lambda self: 'New')

    start_date = fields.Date(string="Start Date", default=fields.Date.today)
    end_date = fields.Date(string="End Date")
    duration = fields.Integer(string="Duration (Months)", compute="_compute_duration", store=True)
    payment_term = fields.Selection([('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')],
                                    string="Payment Term", default='monthly')

    contract_type = fields.Selection([('manual', 'Manual Installment'), ('auto', 'Auto Installment')], string="Type",
                                     default="manual")
    invoice_start_date = fields.Date(string="Invoice Start From", default=fields.Date.today)

    rent = fields.Monetary(string="Rent", currency_field="currency_id")
    deposit = fields.Monetary(string="Security Deposit", currency_field="currency_id")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id)

    total_area = fields.Float(string="Total Area")
    usable_area = fields.Float(string="Usable Area")

    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    property_type = fields.Selection(
        [("land", "Land"), ("residential", "Residential"), ("commercial", "Commercial"), ("industrial", "Industrial")],
        string="Property Type", default='land')
    residential_type = fields.Char(string="Residential Type")

    type = fields.Char(string='Type')
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
            name = self.env['ir.sequence'].next_by_code('rent.contract') or 'New'
            val['name'] = name
        return super(RentContract, self).create(vals)

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                days = (rec.end_date - rec.start_date).days
                rec.duration = days // 30
            else:
                rec.duration = 0

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
        income_account_id = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
        if not income_account_id:
            raise UserError("No income account found. Please configure at least one income account in Accounting.")

        invoice_lines = []
        installments = []

        term_map = {'monthly': 1, 'quarterly': 3, 'yearly': 12}
        months = term_map.get(self.payment_term, 1)
        last_installment_id = self.env['rent.installment'].search(
            [('rent_contract_id', '=', self.id), ('payment_type', '=', 'rent')], order="invoice_date desc", limit=1)
        next_due_date = self.invoice_start_date or self.start_date
        if last_installment_id:
            next_due_date = last_installment_id.invoice_date + relativedelta(months=months)

        if fields.Date.today() < next_due_date:
            raise UserError(f"Next rent invoice can only be created on or after {next_due_date}. "
                            f"Last invoice was generated for {last_installment_id.invoice_date if last_installment_id else 'N/A'}.")

        if next_due_date <= self.end_date:
            rent_amount = self.rent * months
            invoice_lines.append((0, 0, {
                'product_id': self.installment_item_id.id if self.installment_item_id else False,
                'name': f"Rent for {next_due_date}",
                'quantity': 1,
                'price_unit': rent_amount,
                'account_id': income_account_id.id,
            }))
            installments.append({
                'rent_contract_id': self.id,
                'invoice_date': next_due_date,
                'payment_type': 'rent',
                'description': f"Rent Installment for {next_due_date}",
                'amount': rent_amount,
                'currency_id': self.currency_id.id,
            })

        if self.deposit and self.deposit > 0 and not self.deposit_invoice_id:
            invoice_lines.append((0, 0, {
                'product_id': self.deposit_item_id.id if self.deposit_item_id else False,
                'name': f"Security Deposit - {self.name}",
                'quantity': 1,
                'price_unit': self.deposit,
                'account_id': income_account_id.id,
            }))
            installments.append({
                'rent_contract_id': self.id,
                'invoice_date': self.start_date,
                'payment_type': 'deposit',
                'description': f"Security Deposit - {self.name}",
                'amount': self.deposit,
                'currency_id': self.currency_id.id,
            })

        if self.total_maintenance and self.total_maintenance > 0:
            maint_amount = self.total_maintenance
            if self.charge_type == 'area_wise':
                maint_amount *= (self.total_area or 0.0)

            if self.maintenance_type == 'once':
                already_exists_id = self.env['rent.installment'].search(
                    [('rent_contract_id', '=', self.id), ('payment_type', '=', 'maintenance'),
                     ('description', '=', f"Maintenance Charge - {self.name}")], limit=1)
                if not already_exists_id:
                    invoice_lines.append((0, 0, {
                        'name': f"Maintenance Charge - {self.name}",
                        'quantity': 1,
                        'price_unit': maint_amount,
                        'account_id': income_account_id.id,
                    }))
                    installments.append({
                        'rent_contract_id': self.id,
                        'invoice_date': self.start_date,
                        'payment_type': 'maintenance',
                        'description': f"Maintenance Charge - {self.name}",
                        'amount': maint_amount,
                        'currency_id': self.currency_id.id,
                    })

            elif self.maintenance_type == 'recurring':
                already_exists_id = self.env['rent.installment'].search(
                    [('rent_contract_id', '=', self.id), ('payment_type', '=', 'maintenance'),
                     ('invoice_date', '=', next_due_date)], limit=1)
                if not already_exists_id:
                    invoice_lines.append((0, 0, {
                        'name': f"Maintenance for {next_due_date}",
                        'quantity': 1,
                        'price_unit': maint_amount,
                        'account_id': income_account_id.id,
                    }))
                    installments.append({
                        'rent_contract_id': self.id,
                        'invoice_date': next_due_date,
                        'payment_type': 'maintenance',
                        'description': f"Maintenance for {next_due_date}",
                        'amount': maint_amount,
                        'currency_id': self.currency_id.id,
                    })
        for service_id in self.utility_service_ids:
            if service_id.service_type == 'once':
                already_exists_id = self.env['rent.installment'].search(
                    [('rent_contract_id', '=', self.id), ('payment_type', '=', 'utility'),
                     ('description', '=', f"{service_id.service_id.name} (One-time)")], limit=1)
                if not already_exists_id:
                    invoice_lines.append((0, 0, {
                        'product_id': service_id.service_id.id if service_id.service_id else False,
                        'name': f"{service_id.service_id.name} (One-time)",
                        'quantity': 1,
                        'price_unit': service_id.cost,
                        'account_id': income_account_id.id,
                    }))
                    installments.append({
                        'rent_contract_id': self.id,
                        'invoice_date': self.start_date,
                        'payment_type': 'utility',
                        'description': f"{service_id.service_id.name} (One-time)",
                        'amount': service_id.cost,
                        'currency_id': self.currency_id.id,
                    })

            elif service_id.service_type == 'recurring':
                already_exists_id = self.env['rent.installment'].search(
                    [('rent_contract_id', '=', self.id), ('payment_type', '=', 'utility'),
                     ('invoice_date', '=', next_due_date),
                     ('description', '=', f"{service_id.service_id.name} for {next_due_date}")], limit=1)
                if not already_exists_id:
                    invoice_lines.append((0, 0, {
                        'product_id': service_id.service_id.id if service_id.service_id else False,
                        'name': f"{service_id.service_id.name} for {next_due_date}",
                        'quantity': 1,
                        'price_unit': service_id.cost,
                        'account_id': income_account_id.id,
                    }))
                    installments.append({
                        'rent_contract_id': self.id,
                        'invoice_date': next_due_date,
                        'payment_type': 'utility',
                        'description': f"{service_id.service_id.name} for {next_due_date}",
                        'amount': service_id.cost,
                        'currency_id': self.currency_id.id,
                    })

        if not invoice_lines:
            raise UserError("Nothing to invoice for this period.")

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.tenant_id.id,
            'invoice_origin': self.name,
            'invoice_date': next_due_date,
            'currency_id': self.currency_id.id,
            'property_id': self.property_id.id,
            'invoice_line_ids': invoice_lines,
        }
        invoice_id = self.env['account.move'].create(invoice_vals)

        for inst in installments:
            inst['invoice_id'] = invoice_id.id
            self.env['rent.installment'].create(inst)

        if self.deposit and self.deposit > 0 and not self.deposit_invoice_id:
            self.deposit_invoice_id = invoice_id.id

        return {
            'name': 'Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice_id.id,
            'view_mode': 'form',
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
        invoices_id = self.rent_installment_ids.mapped('invoice_id').filtered(
            lambda inv: inv.move_type == 'out_invoice')
        return {
            'name': 'Customer Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('invoice_origin', '=', self.name), ('move_type', 'in', ['out_invoice', 'out_refund']), ],
        }

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = self.env['account.move'].search_count(
                [('invoice_origin', '=', rec.name), ('move_type', 'in', ['out_invoice', 'out_refund'])])

    @api.onchange('property_id')
    def _onchange_property_id(self):
        for rec in self:
            if rec.property_id:
                rec.property_type = rec.property_id.property_type or ''
                rec.residential_type = rec.property_id.residential_type or ''
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

            move_vals = {
                'move_type': 'out_invoice',
                'partner_id': contract_id.tenant_id.id,
                'invoice_date': fields.Date.today(),
                'currency_id': contract_id.currency_id.id,
                'invoice_origin': contract_id.name,
                'invoice_line_ids': [(0, 0, {
                    'product_id': contract_id.penalty_product_id.id if contract_id.penalty_product_id else False,
                    'name': f"Late Fee for overdue rent invoice {installments_id.invoice_id.name}",
                    'quantity': 1,
                    'price_unit': penalty_amount,
                    'account_id': income_account_id.id,
                })],
            }
            invoice_id = self.env['account.move'].create(move_vals)

            self.env['rent.installment'].create({
                'rent_contract_id': contract_id.id,
                'invoice_date': fields.Date.today(),
                'payment_type': 'penalty',
                'description': f"Penalty for invoice {installments_id.invoice_id.name}",
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
            term_map = {'monthly': 1, 'quarterly': 3, 'yearly': 12}
            months = term_map.get(contract_id.payment_term, 1)

            last_installment_id = self.env['rent.installment'].search(
                [('rent_contract_id', '=', contract_id.id), ('payment_type', '=', 'rent')],
                order="invoice_date desc", limit=1)
            next_due_date = contract_id.invoice_start_date or contract_id.start_date
            if last_installment_id:
                next_due_date = last_installment_id.invoice_date + relativedelta(months=months)

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
