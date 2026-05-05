# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""
Cheque record.

One model handles both directions:

* outgoing: we paid a vendor by cheque (drawn on our bank).
* incoming: we received a customer cheque (drawn on the customer bank).

State machine:

  draft -> registered -> presented -> cleared
                              \\-> bounced -> replaced (chained to a new
                                              cheque) or written off
                              \\-> cancelled

Outgoing cheques consume a serial from the cheque book. Incoming cheques
record the issuer bank, account, and cheque number as captured from the
physical instrument.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EhCheque(models.Model):
    _name = 'eh.cheque'
    _description = "Post Dated Cheque"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'value_date desc, id desc'

    name = fields.Char(
        string="Reference",
        required=True, copy=False, default='/',
        tracking=True,
    )
    direction = fields.Selection([
        ('outgoing', "Issued (Payable)"),
        ('incoming', "Received (Receivable)"),
    ], required=True, default='incoming', tracking=True)

    state = fields.Selection([
        ('draft', "Draft"),
        ('registered', "Registered"),
        ('presented', "Presented"),
        ('cleared', "Cleared"),
        ('bounced', "Bounced"),
        ('replaced', "Replaced"),
        ('cancelled', "Cancelled"),
    ], default='draft', required=True, tracking=True)

    cheque_number = fields.Char(
        required=True, copy=False, tracking=True,
        help="Cheque serial number as printed on the cheque.",
    )
    book_id = fields.Many2one(
        'eh.cheque.book', string="Cheque Book",
        domain="[('state', '=', 'in_use'), "
               "('journal_id', '=', journal_id), "
               "('company_id', '=', company_id)]",
        tracking=True,
        help="Required for issued cheques. Drives serial allocation.",
    )
    journal_id = fields.Many2one(
        'account.journal', string="Bank Journal",
        required=True, tracking=True,
        domain="[('type', '=', 'bank')]",
        ondelete='restrict',
    )

    partner_id = fields.Many2one(
        'res.partner', string="Counterparty",
        required=True, tracking=True,
    )
    issuer_bank_name = fields.Char(
        string="Issuer Bank",
        help="For incoming cheques: name of the bank the customer cheque "
             "is drawn on.",
    )
    issuer_account = fields.Char(
        string="Issuer Account",
        help="Customer bank account masked or last 4 digits.",
    )

    amount = fields.Monetary(required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )

    issue_date = fields.Date(
        required=True, default=fields.Date.context_today, tracking=True,
        help="Date the cheque was written or received.",
    )
    value_date = fields.Date(
        required=True, tracking=True,
        help="Date on which the cheque becomes presentable.",
    )

    presented_at = fields.Datetime(readonly=True, tracking=True)
    cleared_at = fields.Datetime(readonly=True, tracking=True)
    bounced_at = fields.Datetime(readonly=True, tracking=True)
    cancelled_at = fields.Datetime(readonly=True, tracking=True)

    presented_by_id = fields.Many2one('res.users', readonly=True)
    cleared_by_id = fields.Many2one('res.users', readonly=True)
    bounced_by_id = fields.Many2one('res.users', readonly=True)
    cancelled_by_id = fields.Many2one('res.users', readonly=True)

    bounce_reason_id = fields.Many2one(
        'eh.cheque.bounce.reason', tracking=True,
    )
    bounce_charges = fields.Monetary(
        help="Bank charges levied for the bounce, captured on customer side.",
    )
    bounce_notes = fields.Text()

    replaced_by_id = fields.Many2one(
        'eh.cheque', string="Replaced By", readonly=True, copy=False,
        help="If this cheque was replaced after a bounce, the new cheque.",
    )
    replaces_id = fields.Many2one(
        'eh.cheque', string="Replaces", readonly=True, copy=False,
        help="The original cheque this record replaces.",
    )

    invoice_id = fields.Many2one(
        'account.move', string="Linked Invoice",
        domain="[('move_type', 'in', ['out_invoice', 'in_invoice', "
               "'out_refund', 'in_refund'])]",
    )
    payment_id = fields.Many2one(
        'account.payment', string="Linked Payment", readonly=True,
    )

    notes = fields.Text()

    present_move_id = fields.Many2one(
        'account.move', readonly=True, copy=False,
        help="Journal entry posted on present (deposit / issue).",
    )
    clear_move_id = fields.Many2one(
        'account.move', readonly=True, copy=False,
        help="Journal entry posted on clearance (suspense → bank).",
    )
    bounce_move_id = fields.Many2one(
        'account.move', readonly=True, copy=False,
        help="Reversal of the present entry, posted on bounce.",
    )

    is_overdue = fields.Boolean(
        compute='_compute_is_overdue', store=False, search='_search_is_overdue',
    )

    _uniq_book_serial = models.Constraint(
        'unique(book_id, cheque_number)',
        'A cheque serial cannot be reused within the same book.',
    )

    # ---- compute ----

    @api.depends('value_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for cheque in self:
            cheque.is_overdue = bool(
                cheque.value_date
                and cheque.value_date < today
                and cheque.state in ('draft', 'registered', 'presented')
            )

    def _search_is_overdue(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_("Unsupported search operator on is_overdue."))
        positive = bool(value) if operator == '=' else not bool(value)
        today = fields.Date.context_today(self)
        domain = [
            ('value_date', '<', today),
            ('state', 'in', ['draft', 'registered', 'presented']),
        ]
        return domain if positive else ['!'] + domain

    # ---- onchange ----

    @api.onchange('direction', 'journal_id')
    def _onchange_direction_journal(self):
        if self.direction == 'incoming':
            self.book_id = False

    @api.onchange('book_id')
    def _onchange_book(self):
        if self.book_id and self.direction == 'outgoing':
            if self.book_id.state == 'in_use' and self.book_id.next_number <= self.book_id.end_number:
                self.cheque_number = str(self.book_id.next_number)

    # ---- create ----

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                seq = self.env['ir.sequence'].next_by_code('eh.cheque') or '/'
                vals['name'] = seq
        cheques = super().create(vals_list)
        for cheque in cheques:
            if cheque.direction == 'outgoing' and cheque.book_id:
                cheque._validate_serial_against_book()
        return cheques

    def _validate_serial_against_book(self):
        self.ensure_one()
        if not self.cheque_number or not self.cheque_number.isdigit():
            raise UserError(_(
                "Outgoing cheque serial must be numeric within a cheque book.",
            ))
        serial = int(self.cheque_number)
        if not (self.book_id.start_number <= serial <= self.book_id.end_number):
            raise UserError(_(
                "Cheque serial %(serial)s is outside book range "
                "%(start)s-%(end)s.",
                serial=serial,
                start=self.book_id.start_number,
                end=self.book_id.end_number,
            ))

    # ---- transitions ----

    def action_register(self):
        for cheque in self:
            if cheque.state != 'draft':
                raise UserError(_(
                    "Only draft cheques can be registered.",
                ))
            if cheque.direction == 'outgoing':
                if not cheque.book_id:
                    raise UserError(_(
                        "Issued cheques require a cheque book.",
                    ))
                # Lock the book row before reading next_number so two
                # concurrent registrations on the same book serialise
                # rather than racing. The book unique-constraint on
                # (book_id, cheque_number) is the safety net; the lock
                # turns a race into a queue.
                cheque.book_id._lock_for_update()
                cheque._validate_serial_against_book()
                book = cheque.book_id
                if book.state != 'in_use':
                    raise UserError(_(
                        "Cheque book %s is not active.", book.name,
                    ))
                serial = int(cheque.cheque_number)
                if serial != book.next_number:
                    raise UserError(_(
                        "Cheque serial %(serial)s does not match the "
                        "next available serial %(next)s on book "
                        "%(book)s. Refresh and try again, or close gaps "
                        "in the book first.",
                        serial=serial,
                        next=book.next_number,
                        book=book.name,
                    ))
                book.next_number = serial + 1
                if book.next_number > book.end_number:
                    book.state = 'exhausted'
            cheque.state = 'registered'

    def action_present(self):
        today = fields.Date.context_today(self)
        for cheque in self:
            if cheque.state not in ('registered',):
                raise UserError(_(
                    "Only registered cheques can be presented to the bank.",
                ))
            # A post-dated cheque is not negotiable until the value date.
            # Real banks refuse to deposit it; presenting in Odoo before
            # the value date would post the suspense JE in advance and
            # mismatch when the bank actually clears later. Block early
            # so finance follows the calendar. Use the eh_pdc_force_early
            # context key if you genuinely need to backfill (data import,
            # opening balance migrations).
            if cheque.value_date and cheque.value_date > today and \
                    not self.env.context.get('eh_pdc_force_early'):
                raise UserError(_(
                    "Cheque %(name)s cannot be presented before its value "
                    "date %(value_date)s. Today is %(today)s.",
                    name=cheque.cheque_number or cheque.id,
                    value_date=fields.Date.to_string(cheque.value_date),
                    today=fields.Date.to_string(today),
                ))
            move = cheque._post_pdc_move('present')
            cheque.write({
                'state': 'presented',
                'presented_at': fields.Datetime.now(),
                'presented_by_id': self.env.user.id,
                'present_move_id': move.id,
            })

    def action_clear(self):
        for cheque in self:
            if cheque.state != 'presented':
                raise UserError(_(
                    "Only presented cheques can be marked as cleared.",
                ))
            move = cheque._post_pdc_move('clear')
            cheque.write({
                'state': 'cleared',
                'cleared_at': fields.Datetime.now(),
                'cleared_by_id': self.env.user.id,
                'clear_move_id': move.id,
            })

    def action_cancel(self):
        for cheque in self:
            if cheque.state in ('cleared', 'replaced'):
                raise UserError(_(
                    "Cleared or replaced cheques cannot be cancelled.",
                ))
            cheque.write({
                'state': 'cancelled',
                'cancelled_at': fields.Datetime.now(),
                'cancelled_by_id': self.env.user.id,
            })

    def action_open_bounce_wizard(self):
        self.ensure_one()
        if self.state != 'presented':
            raise UserError(_(
                "Only presented cheques can be bounced.",
            ))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'eh.cheque.bounce.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_cheque_id': self.id},
        }

    def action_open_replace_wizard(self):
        self.ensure_one()
        if self.state != 'bounced':
            raise UserError(_(
                "Only bounced cheques can be replaced.",
            ))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'eh.cheque.replace.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_cheque_id': self.id},
        }

    def _mark_bounced(self, reason, charges=0.0, notes=None):
        for cheque in self:
            reversal = False
            if cheque.present_move_id and cheque.present_move_id.state == 'posted':
                reversal = cheque._post_pdc_move(
                    'bounce', reverse_of=cheque.present_move_id,
                )
            cheque.write({
                'state': 'bounced',
                'bounced_at': fields.Datetime.now(),
                'bounced_by_id': self.env.user.id,
                'bounce_reason_id': reason.id if reason else False,
                'bounce_charges': charges or 0.0,
                'bounce_notes': notes or False,
                'bounce_move_id': reversal.id if reversal else False,
            })
            cheque.message_post(
                body=_("Cheque bounced: %s",
                       reason.name if reason else _("(no reason)")),
            )

    # ---- accounting helpers ----

    def _pdc_resolve_accounts(self):
        """Return (suspense_account, partner_account, bank_account) for posting.

        Hard fails if any account is unresolvable so we never post a
        broken or one-sided entry.
        """
        self.ensure_one()
        journal = self.journal_id
        suspense = journal.suspense_account_id
        if not suspense:
            raise UserError(_(
                "Bank journal %s has no Suspense Account configured. "
                "Set it on the journal before processing PDC accounting.",
                journal.display_name,
            ))
        bank = journal.default_account_id
        if not bank:
            raise UserError(_(
                "Bank journal %s has no Default Account configured.",
                journal.display_name,
            ))
        if self.direction == 'incoming':
            partner_account = self.partner_id.with_company(
                self.company_id,
            ).property_account_receivable_id
        else:
            partner_account = self.partner_id.with_company(
                self.company_id,
            ).property_account_payable_id
        if not partner_account:
            raise UserError(_(
                "Partner %s has no %s account configured for company %s.",
                self.partner_id.display_name,
                'receivable' if self.direction == 'incoming' else 'payable',
                self.company_id.display_name,
            ))
        return suspense, partner_account, bank

    def _post_pdc_move(self, transition, reverse_of=False):
        """Post the journal entry for a PDC state transition.

        transitions: 'present', 'clear', 'bounce'
        For 'bounce' we post a reversal of `reverse_of` (the present move).
        """
        self.ensure_one()
        suspense, partner_acc, bank_acc = self._pdc_resolve_accounts()
        amount = self.amount
        currency = self.currency_id
        ref = _("PDC %s: %s") % (transition, self.name)
        # Pick journal: use bank journal for present/clear; for bounce use
        # the same journal as the original present move.
        if transition == 'bounce' and reverse_of:
            return reverse_of._reverse_moves(
                [{'date': fields.Date.context_today(self), 'ref': ref}],
                cancel=False,
            )
        if self.direction == 'incoming':
            if transition == 'present':
                # DR suspense, CR receivable
                debit_acc, credit_acc = suspense, partner_acc
            else:  # clear
                # DR bank, CR suspense
                debit_acc, credit_acc = bank_acc, suspense
        else:  # outgoing
            if transition == 'present':
                # DR payable, CR suspense
                debit_acc, credit_acc = partner_acc, suspense
            else:  # clear
                # DR suspense, CR bank
                debit_acc, credit_acc = suspense, bank_acc
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': ref,
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {
                    'name': ref,
                    'account_id': debit_acc.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': currency.id,
                    'debit': amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': ref,
                    'account_id': credit_acc.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': currency.id,
                    'debit': 0.0,
                    'credit': amount,
                }),
            ],
        }
        move = self.env['account.move'].sudo().create(move_vals)
        move.action_post()
        return move

    def _mark_replaced_by(self, new_cheque):
        self.ensure_one()
        self.write({
            'state': 'replaced',
            'replaced_by_id': new_cheque.id,
        })
        new_cheque.write({'replaces_id': self.id})

    # ---- cron ----

    @api.model
    def _cron_auto_present(self, batch_size=200):
        """Move registered cheques to presented when value_date arrives.

        Per record try/except so a single failure does not stop the batch.
        Audit trail: each transition is tracked through the standard
        message_post chain via state tracking.
        """
        today = fields.Date.context_today(self)
        domain = [
            ('state', '=', 'registered'),
            ('value_date', '<=', today),
        ]
        cheques = self.search(domain, limit=batch_size)
        for cheque in cheques:
            try:
                cheque.action_present()
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "Auto presentation failed for cheque %s: %s",
                    cheque.display_name, exc,
                )

    # ---- helpers ----

    @api.depends(
        'cheque_number', 'partner_id', 'partner_id.display_name',
        'amount', 'currency_id', 'currency_id.name',
    )
    def _compute_display_name(self):
        for cheque in self:
            partner_label = (
                cheque.partner_id.display_name
                if cheque.partner_id else ''
            )
            label = "%s / %s" % (cheque.cheque_number or '', partner_label)
            if cheque.amount and cheque.currency_id:
                label = "%s (%s)" % (label, cheque.currency_id.name)
            cheque.display_name = label
