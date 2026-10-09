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
         ('finance_review', 'Finance Review'), ('approved', 'Approved'), ('settled', 'Settled'),
         ('cancelled', 'Cancelled')],
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

    def _get_finance_users(self):
        """Find users representing the Finance / Accounting team who can review & approve Move-Out."""
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

        # 2. Users in Move-Out Finance Approver group
        finance_group = self.env.ref('eg_property_management.group_property_finance_approver', raise_if_not_found=False)
        if finance_group:
            users = self.env['res.users'].search([
                (groups_field, 'in', finance_group.ids),
                ('share', '=', False),
                ('active', '=', True),
            ])
            if users:
                return users

        # 3. Fallback to standard Odoo Accounting / Invoicing groups
        groups = [
            'account.group_account_user',
            'account.group_account_invoice',
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

    def _send_system_notification(self, title, message, partners, activity_summary=None, activity_user_ids=None):
        """Send in-system notification directly to partners and users:
        1. Posts in Move-Out chatter and Contract chatter with forced notification_type='in_app'
           (increments Discuss systray unread badge, no emails required).
        2. Sends real-time pop-up notification via bus.bus to connected users.
        3. Schedules mail.activity for approver users.
        """
        self.ensure_one()
        if not partners:
            return

        # 1. Post notification in Move-Out chatter
        msg = self.message_post(
            body=f"<b>{title}</b><br/>{message}",
            subject=title,
            partner_ids=partners.ids,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
        if msg and msg.notification_ids:
            try:
                msg.notification_ids.sudo().write({'notification_type': 'inbox'})
            except Exception:
                pass

        # Also post in Contract chatter
        if self.rent_contract_id:
            try:
                c_msg = self.rent_contract_id.message_post(
                    body=f"<b>{title}</b><br/>{message}",
                    subject=title,
                    partner_ids=partners.ids,
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
                if c_msg and c_msg.notification_ids:
                    try:
                        c_msg.notification_ids.sudo().write({'notification_type': 'inbox'})
                    except Exception:
                        pass
            except Exception:
                pass

        # 2. Real-time pop-up notification via bus.bus
        for partner in partners:
            try:
                self.env['bus.bus']._sendone(
                    partner,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': title,
                        'message': message,
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
                            'title': title,
                            'message': message,
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

    def action_submit_finance_review(self):
        for rec in self:
            rec.write({
                'state': 'finance_review',
                'finance_reviewed_by': self.env.user.id,
                'finance_reviewed_date': fields.Datetime.now(),
            })

            finance_users = rec._get_finance_users()
            finance_partners = finance_users.mapped('partner_id')
            curr = rec.currency_id.symbol or ''
            title = f"Move-Out Deposit Release Approval Needed: {rec.rent_contract_id.name}"
            message = (
                f"Move-Out record for contract <b>{rec.rent_contract_id.name}</b> "
                f"(Property: <b>{rec.property_id.name or 'N/A'}</b>, Tenant: <b>{rec.tenant_id.name or 'N/A'}</b>) "
                f"has been submitted for Finance Review.<br/>"
                f"Deposit Received: <b>{rec.deposit_received} {curr}</b> | "
                f"Total Deductions: <b>{rec.total_deduction_amount} {curr}</b> | "
                f"Release / Refund: <b>{rec.deposit_release_amount} {curr}</b>.<br/>"
                f"Please review deductions and approve the deposit release."
            )
            rec._send_system_notification(
                title=title,
                message=message,
                partners=finance_partners,
                activity_summary="Approve Move-Out Deposit Release",
                activity_user_ids=finance_users,
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Submitted for Finance Review',
                'message': 'Move-out record submitted. Finance team has been notified within the system.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_approve(self):
        for rec in self:
            is_approver = (
                rec.env.user.has_group('eg_property_management.group_property_finance_approver') or
                rec.env.user.has_group('base.group_system') or
                rec.env.user.id in rec._get_finance_users().ids
            )
            if not is_approver:
                raise UserError("You do not have access rights to approve Move-Out deposit releases. "
                                "Only users with the 'Finance Approver (Move-Out)' access right or Administrators can approve.")

            rec.write({
                'state': 'approved',
                'approved_by': rec.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

            # Mark pending activity as done
            try:
                rec.activity_feedback(
                    ['mail.mail_activity_data_todo'],
                    feedback=f"Deposit release approved by {rec.env.user.name}."
                )
            except Exception:
                pass

            curr = rec.currency_id.symbol or ''
            title = f"Move-Out Deposit Release Approved: {rec.rent_contract_id.name}"
            message = (
                f"Move-Out deposit release for contract <b>{rec.rent_contract_id.name}</b> "
                f"has been approved by <b>{rec.env.user.name}</b>.<br/>"
                f"Deposit Received: <b>{rec.deposit_received} {curr}</b> | "
                f"Total Deductions: <b>{rec.total_deduction_amount} {curr}</b> | "
                f"Approved Release: <b>{rec.deposit_release_amount} {curr}</b>."
            )
            rec.message_post(body=f"<b>{title}</b><br/>{message}", subtype_xmlid='mail.mt_comment')

            # Notify contract manager / creator if different from approver
            notif_partners = self.env['res.partner']
            if rec.rent_contract_id.user_id and rec.rent_contract_id.user_id.partner_id:
                notif_partners |= rec.rent_contract_id.user_id.partner_id
            if rec.create_uid and rec.create_uid.partner_id:
                notif_partners |= rec.create_uid.partner_id
            notif_partners = notif_partners - rec.env.user.partner_id
            if notif_partners:
                rec._send_system_notification(title=title, message=message, partners=notif_partners)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Deposit Release Approved',
                'message': 'Move-out deposit release has been successfully approved.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_mark_deduction_transfer_done(self):
        for rec in self:
            rec.deduction_transfer_done = True

    def action_settle(self):
        """Step 15. The only place that frees the property: calls the
        contract's existing action_state_terminate(), unchanged, and explicitly
        sets the linked property to 'available' (Vacant)."""
        for rec in self:
            if rec.state != 'approved':
                raise UserError("The deposit release must be approved before settling the Move-Out.")
            if rec.rent_contract_id:
                rec.rent_contract_id.action_state_terminate()
            if rec.property_id:
                rec.property_id.write({'state': 'available'})
            rec.state = 'settled'
            rec.message_post(
                body=f"Move-Out has been settled. Linked property <b>{rec.property_id.name or 'N/A'}</b> is now <b>Vacant</b>.",
                subtype_xmlid='mail.mt_comment'
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Move-Out Settled',
                'message': 'Move-out settled successfully. The linked property is now Vacant.',
                'type': 'success',
                'sticky': False,
            }
        }

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'settled':
            for rec in self:
                if rec.property_id:
                    rec.property_id.write({'state': 'available'})
        return res

    def action_cancel(self):
        """Cancel the Move-Out process at any stage unless it is already settled."""
        for rec in self:
            if rec.state == 'settled':
                raise UserError("A settled Move-Out cannot be cancelled.")
            rec.state = 'cancelled'

            # Cancel any scheduled activities for this Move-Out
            try:
                rec.activity_unlink(['mail.mail_activity_data_todo'])
            except Exception:
                pass

            rec.message_post(
                body=f"Move-Out record has been cancelled by <b>{self.env.user.name}</b>.",
                subtype_xmlid='mail.mt_comment'
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Move-Out Cancelled',
                'message': 'Move-out record has been cancelled.',
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_reset_draft(self):
        """Aborting/restarting a Move-Out also returns the contract's own
        state to 'running' (only if it's currently 'move_out' - never
        overwrites a state the contract reached some other way), so the
        contract doesn't sit indefinitely on the 'Move-Out Process'
        statusbar step with nothing actually in progress."""
        for rec in self:
            if rec.state == 'settled':
                raise UserError("A settled Move-Out cannot be reset to draft.")
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
