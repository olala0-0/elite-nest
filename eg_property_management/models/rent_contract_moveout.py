import base64

from odoo import api, fields, models
from odoo.exceptions import UserError


class RentContractMoveOut(models.Model):
    _name = 'rent.contract.moveout'
    _description = 'Rent Contract Move-Out'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    rent_contract_id = fields.Many2one(comodel_name='rent.contract', string='Rent Contract',
                                       required=True, ondelete='cascade')
    property_id = fields.Many2one(related='rent_contract_id.property_id', string='Property',
                                  store=True, readonly=True)
    tenant_id = fields.Many2one(related='rent_contract_id.tenant_id', string='Tenant',
                                store=True, readonly=True)
    company_id = fields.Many2one(related='rent_contract_id.company_id', string='Company',
                                 store=True, readonly=True)
    currency_id = fields.Many2one(related='rent_contract_id.currency_id', string='Currency',
                                  store=True, readonly=True)

    # Step 1-2: Renewal notice / Tenant decision. "No" branch is the
    # existing rent.contract.extend.wizard - this record only exists for
    # the "Yes, moving out" branch.
    renewal_notice_date = fields.Date(string='Renewal Notice Sent On')

    # Step 3
    process_shared_date = fields.Date(string='Move-Out Process Shared On')

    # Step 4: Utilities clearance - the three named clearances from the
    # diagram, plus a free attachment slot each.
    dewa_clearance_received = fields.Boolean(string='DEWA Clearance Received')
    dewa_clearance_date = fields.Date(string='DEWA Clearance Date')
    dewa_clearance_file = fields.Binary(string='DEWA Clearance Document')
    dewa_clearance_filename = fields.Char(string='DEWA Clearance Filename')

    logic_utilities_clearance_received = fields.Boolean(string='Logic Utilities Clearance Received')
    logic_utilities_clearance_date = fields.Date(string='Logic Utilities Clearance Date')
    logic_utilities_clearance_file = fields.Binary(string='Logic Utilities Clearance Document')
    logic_utilities_clearance_filename = fields.Char(string='Logic Utilities Clearance Filename')

    lootah_gas_clearance_received = fields.Boolean(string='Lootah Gas Clearance Received')
    lootah_gas_clearance_date = fields.Date(string='Lootah Gas Clearance Date')
    lootah_gas_clearance_file = fields.Binary(string='Lootah Gas Clearance Document')
    lootah_gas_clearance_filename = fields.Char(string='Lootah Gas Clearance Filename')

    # Step 5
    noc_issued = fields.Boolean(string='Move-Out NOC Issued', readonly=True)
    noc_date = fields.Date(string='NOC Issue Date', readonly=True)
    noc_document = fields.Binary(string='NOC Document')
    noc_filename = fields.Char(string='NOC Filename')

    # Step 6
    key_handover_date = fields.Date(string='Key Handover Date')

    # Steps 7-10
    final_inspection_id = fields.Many2one(
        comodel_name='property.inspection', string='Final Inspection', copy=False,
        domain="[('inspection_type', '=', 'move_out')]")

    # Steps 11-14
    deduction_line_ids = fields.One2many(comodel_name='rent.contract.moveout.deduction',
                                         inverse_name='moveout_id', string='Deductions')
    finance_reviewed_by = fields.Many2one(comodel_name='res.users', string='Finance Reviewed By', readonly=True)
    finance_reviewed_date = fields.Datetime(string='Finance Reviewed On', readonly=True)
    approved_by = fields.Many2one(comodel_name='res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved On', readonly=True)
    deduction_transfer_done = fields.Boolean(string='Deduction Transfer Done', readonly=True)

    deduction_invoice_id = fields.Many2one(comodel_name='account.move', string='Deduction Invoice',
                                           readonly=True, copy=False)
    refund_move_id = fields.Many2one(comodel_name='account.move', string='Deposit Refund Credit Note',
                                     readonly=True, copy=False)

    deposit_received = fields.Monetary(string='Deposit Received', currency_field='currency_id',
                                       compute='_compute_deposit_figures')
    total_deduction_amount = fields.Monetary(string='Total Deductions', currency_field='currency_id',
                                             compute='_compute_deposit_figures')
    deposit_release_amount = fields.Monetary(
        string='Deposit Release / (Shortfall)', currency_field='currency_id',
        compute='_compute_deposit_figures',
        help="Deposit Received minus Total Deductions. Positive = refund "
             "due to tenant, Negative = tenant still owes a shortfall on "
             "top of the deposit. Recalculates live from the deduction "
             "lines below until Finalize Deductions turns it into real "
             "accounting documents (Deduction Invoice / Refund Credit "
             "Note), after which those documents are the source of truth.")

    state = fields.Selection(
        [('draft', 'Draft'), ('clearance_pending', 'Clearance Pending'), ('inspection_done', 'Final Inspection'),
         ('finance_review', 'Finance Review'), ('approved', 'Approved'), ('settled', 'Settled')],
        string='Status', default='draft', tracking=True)

    @api.depends('deduction_line_ids.amount', 'rent_contract_id')
    def _compute_deposit_figures(self):
        for rec in self:
            deposit_received = 0.0
            if rec.rent_contract_id:
                deposit_received = rec.rent_contract_id._get_deposit_summary()['deposit_received']
            total_deductions = sum(rec.deduction_line_ids.mapped('amount'))
            rec.deposit_received = deposit_received
            rec.total_deduction_amount = total_deductions
            rec.deposit_release_amount = deposit_received - total_deductions

    def action_create_or_open_inspection(self):
        self.ensure_one()
        if not self.final_inspection_id:
            self.final_inspection_id = self.env['property.inspection'].create({
                'rent_contract_id': self.rent_contract_id.id,
                'property_id': self.property_id.id,
                'tenant_id': self.tenant_id.id,
                'inspection_type': 'move_out',
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'property.inspection',
            'res_id': self.final_inspection_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_pull_deductions_from_inspection(self):
        """Populate deduction lines from every checklist line on the Final
        Inspection that isn't OK. Safe to click more than once - only adds
        lines for inspection lines that don't already have one, so it never
        duplicates or overwrites a deduction Finance already edited by hand."""
        self.ensure_one()
        if not self.final_inspection_id:
            raise UserError("Run the Final Inspection first.")
        existing_source_lines = self.deduction_line_ids.mapped('inspection_line_id')
        new_lines = self.final_inspection_id.line_ids.filtered(
            lambda line: line.condition != 'ok' and line not in existing_source_lines
        )
        for line in new_lines:
            self.env['rent.contract.moveout.deduction'].create({
                'moveout_id': self.id,
                'inspection_line_id': line.id,
                'charge_category': 'dilapidation',
                'description': f"{line.area + ' - ' if line.area else ''}{line.name} ({line.condition})",
                'amount': line.estimated_cost,
            })

    def action_finalize_deductions(self):
        """Turns the approved deduction lines into real accounting
        documents, reusing the exact same building blocks
        action_create_invoice() already uses for rent/deposit/maintenance:
        _prepare_invoice_line(), the same income-account resolution, and
        the same "create as draft, a human posts it in Accounting" pattern
        used everywhere else in this module - nothing here auto-posts.

        1. One consolidated draft customer invoice for every deduction line
           not yet invoiced (Penalty / Dilapidation / Shortfall Rent), each
           also recorded as its own rent.installment so it shows up as its
           own row on the tenant statement, exactly like rent/maintenance
           charges already do.
        2. If Deposit Received exceeds Total Deductions, a draft refund
           credit note (out_refund) for the surplus - the tenant statement
           already renders any posted out_refund linked to this contract,
           so once someone posts this credit note in Accounting it appears
           there automatically, no separate "move-out report" needed.
           If deductions exceed the deposit, no refund is created; the
           tenant simply owes the deduction invoice above, same as any
           other invoice, reconciled against the deposit through normal
           Accounting AR management.

        One-time action: raises if this Move-Out has already been
        finalized, rather than silently creating a second invoice and
        losing track of the first one - if a deduction needs correcting
        after finalizing, fix it in Accounting directly (standard invoice/
        credit note correction), not by re-running this."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError("The deposit release must be approved before finalizing deductions.")
        if self.deduction_invoice_id or self.refund_move_id:
            raise UserError("This Move-Out has already been finalized.")

        contract = self.rent_contract_id
        if not contract.tenant_id:
            raise UserError("Contract has no Tenant/Customer set.")

        lines_to_invoice = self.deduction_line_ids.filtered(lambda line: not line.installment_id and line.amount)
        if lines_to_invoice:
            income_account_id = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
            if not income_account_id:
                raise UserError("No income account found. Please configure at least one income account in Accounting.")

            invoice_settings = contract._get_invoice_settings()
            product_by_category = {
                'penalty': invoice_settings['penalty_product'],
                'dilapidation': invoice_settings['dilapidation_product'],
                'shortfall_rent': invoice_settings['shortfall_rent_product'],
            }
            invoice_lines = [
                contract._prepare_invoice_line(
                    product_by_category.get(line.charge_category), line.description, line.amount, income_account_id,
                )
                for line in lines_to_invoice
            ]
            invoice_id = self.env['account.move'].with_context(skip_sync_installment=True).create({
                'move_type': 'out_invoice',
                'partner_id': contract.tenant_id.id,
                'invoice_origin': contract.name,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
                'currency_id': contract.currency_id.id,
                'property_id': contract.property_id.id,
                'rent_contract_id': contract.id,
                'invoice_line_ids': invoice_lines,
            })
            self.deduction_invoice_id = invoice_id.id
            for line in lines_to_invoice:
                installment_id = self.env['rent.installment'].create({
                    'rent_contract_id': contract.id,
                    'invoice_date': fields.Date.today(),
                    'payment_type': line.charge_category,
                    'description': line.description,
                    'amount': line.amount,
                    'currency_id': contract.currency_id.id,
                    'invoice_id': invoice_id.id,
                })
                line.installment_id = installment_id.id

        if not self.refund_move_id:
            surplus = self.deposit_received - self.total_deduction_amount
            if surplus > 0.005:
                income_account_id = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
                if not income_account_id:
                    raise UserError("No income account found. Please configure at least one income account in Accounting.")
                refund_id = self.env['account.move'].with_context(skip_sync_installment=True).create({
                    'move_type': 'out_refund',
                    'partner_id': contract.tenant_id.id,
                    'invoice_origin': contract.name,
                    'invoice_date': fields.Date.today(),
                    'currency_id': contract.currency_id.id,
                    'property_id': contract.property_id.id,
                    'rent_contract_id': contract.id,
                    'invoice_line_ids': [contract._prepare_invoice_line(
                        False, "Security Deposit Refund - Move-Out Settlement", surplus, income_account_id,
                    )],
                })
                self.refund_move_id = refund_id.id

    def action_start_clearance(self):
        for rec in self:
            rec.state = 'clearance_pending'

    def action_mark_inspection_done(self):
        for rec in self:
            rec.state = 'inspection_done'

    def action_issue_noc(self):
        for rec in self:
            rec.write({'noc_issued': True, 'noc_date': fields.Date.today()})

    def action_send_noc_email(self):
        """Emails the tenant the NOC as a PDF attachment, reusing the same
        mail.mail.create(...).send() pattern already used elsewhere in this
        module. Separate from action_issue_noc() (which just marks the NOC
        official) so re-sending doesn't re-issue it, and issuing it doesn't
        force an email before the document is ready to send."""
        for rec in self:
            if not rec.noc_issued:
                raise UserError("Issue the NOC before sending it.")
            if not rec.tenant_id.email:
                raise UserError(f"{rec.tenant_id.name or 'The tenant'} has no email address on file.")
            pdf_content, _report_type = self.env['ir.actions.report']._render_qweb_pdf(
                'eg_property_management.action_report_moveout_noc', res_ids=rec.ids
            )
            mail_values = {
                'subject': f"Move-Out NOC - {rec.rent_contract_id.name}",
                'body_html': f"""
                    <p>Dear {rec.tenant_id.name},</p>
                    <p>Please find attached your Move-Out No Objection Certificate (NOC) for
                    <b>{rec.property_id.name or 'your property'}</b>.</p>
                    <p>Regards,<br/>{rec.company_id.name}</p>
                """,
                'email_to': rec.tenant_id.email,
                'attachment_ids': [(0, 0, {
                    'name': f"Move-Out NOC - {rec.rent_contract_id.name}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'rent.contract.moveout',
                    'res_id': rec.id,
                })],
            }
            self.env['mail.mail'].create(mail_values).send()

    def action_submit_finance_review(self):
        for rec in self:
            rec.write({
                'state': 'finance_review',
                'finance_reviewed_by': self.env.user.id,
                'finance_reviewed_date': fields.Datetime.now(),
            })

    def action_approve(self):
        """Step 12 (diagram names a specific person - "Ms. Gawhar" - as a
        stand-in for "the admin approves"; see MOVE_IN_MOVE_OUT_PLAN.md
        section 8.3). Gated on Odoo's built-in Administrator group, not a
        named person or a new custom field/group."""
        for rec in self:
            if not rec.env.user.has_group('base.group_system'):
                raise UserError("Only an Administrator can approve the deposit release.")
            rec.write({
                'state': 'approved',
                'approved_by': rec.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

    def action_mark_deduction_transfer_done(self):
        for rec in self:
            rec.deduction_transfer_done = True

    def action_settle(self):
        """Step 15. The only place that frees the property: calls the
        contract's existing action_state_terminate(), unchanged, exactly as
        if someone had clicked "Terminate Contract" by hand. Everything
        before this point is informational/tracking only - clicking through
        earlier steps never touches the contract or the property."""
        for rec in self:
            if rec.state != 'approved':
                raise UserError("The deposit release must be approved before settling the Move-Out.")
            rec.rent_contract_id.action_state_terminate()
            rec.state = 'settled'

    def action_reset_draft(self):
        """Aborting/restarting a Move-Out also returns the contract's own
        state to 'running' (only if it's currently 'move_out' - never
        overwrites a state the contract reached some other way), so the
        contract doesn't sit indefinitely on the 'Move-Out Process'
        statusbar step with nothing actually in progress."""
        for rec in self:
            rec.state = 'draft'
            if rec.rent_contract_id.state == 'move_out':
                rec.rent_contract_id.state = 'running'


class RentContractMoveOutDeduction(models.Model):
    _name = 'rent.contract.moveout.deduction'
    _description = 'Rent Contract Move-Out Deduction'
    _order = 'id'

    moveout_id = fields.Many2one(comodel_name='rent.contract.moveout', string='Move-Out',
                                 required=True, ondelete='cascade')
    inspection_line_id = fields.Many2one(comodel_name='property.inspection.line',
                                         string='Source Inspection Line', readonly=True)
    charge_category = fields.Selection(
        [('penalty', 'Penalty Charges'), ('dilapidation', 'Dilapidation'), ('shortfall_rent', 'Shortfall Rent')],
        string='Category', required=True, default='dilapidation',
        help="Matches the accounting design's Early Termination categories "
             "(Penalty / Dilapidation / Shortfall Rent), so Finalize "
             "Deductions can route each line to the correct Dr/Cr entry "
             "without guessing.")
    description = fields.Char(string='Description', required=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one(related='moveout_id.currency_id', string='Currency',
                                  store=True, readonly=True)
    installment_id = fields.Many2one(comodel_name='rent.installment', string='Installment',
                                     readonly=True, copy=False,
                                     help="Set once Finalize Deductions has invoiced this line. "
                                          "Locks the line from further edits so the deduction "
                                          "shown here can never drift from what was actually "
                                          "invoiced.")
