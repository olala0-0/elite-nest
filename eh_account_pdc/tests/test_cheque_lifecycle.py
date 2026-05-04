# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Cheque lifecycle tests: register, present, clear, cancel."""

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import EhPdcTestCase


@tagged('eh_account_pdc', 'integration', 'post_install', '-at_install')
class TestChequeLifecycle(EhPdcTestCase):

    def _make_outgoing(self, **overrides):
        vals = {
            'direction': 'outgoing',
            'partner_id': self.partner_a.id,
            'journal_id': self.bank_journal.id,
            'book_id': self.book.id,
            'cheque_number': '1',
            'amount': 1000.0,
            'currency_id': self.company.currency_id.id,
            'company_id': self.company.id,
            'issue_date': self.today,
            'value_date': self.today,
        }
        vals.update(overrides)
        return self.env['eh.cheque'].create(vals)

    def _make_incoming(self, **overrides):
        vals = {
            'direction': 'incoming',
            'partner_id': self.partner_a.id,
            'journal_id': self.bank_journal.id,
            'cheque_number': 'CUST-12345',
            'issuer_bank_name': 'ABC Bank',
            'amount': 500.0,
            'currency_id': self.company.currency_id.id,
            'company_id': self.company.id,
            'issue_date': self.today,
            'value_date': self.today,
        }
        vals.update(overrides)
        return self.env['eh.cheque'].create(vals)

    # ---- creation ----

    def test_create_assigns_sequence_reference(self):
        cheque = self._make_incoming()
        self.assertNotEqual(cheque.name, '/')
        self.assertTrue(cheque.name.startswith('CHQ/'))

    def test_outgoing_cheque_serial_must_be_in_range(self):
        with self.assertRaises(UserError):
            self._make_outgoing(cheque_number='999')

    def test_uniq_serial_within_book(self):
        self._make_outgoing(cheque_number='1')
        with self.assertRaises(Exception):
            self._make_outgoing(cheque_number='1')

    # ---- transitions ----

    def test_register_advances_book_pointer_when_serial_matches(self):
        cheque = self._make_outgoing(cheque_number='1')
        cheque.action_register()
        self.assertEqual(cheque.state, 'registered')
        self.assertEqual(self.book.next_number, 2)

    def test_register_outgoing_requires_book(self):
        cheque = self._make_outgoing()
        cheque.book_id = False
        with self.assertRaises(UserError):
            cheque.action_register()

    def test_present_only_from_registered(self):
        cheque = self._make_incoming()
        with self.assertRaises(UserError):
            cheque.action_present()
        cheque.action_register()
        cheque.action_present()
        self.assertEqual(cheque.state, 'presented')
        self.assertEqual(cheque.presented_by_id, self.env.user)
        self.assertTrue(cheque.presented_at)

    def test_clear_only_from_presented(self):
        cheque = self._make_incoming()
        cheque.action_register()
        with self.assertRaises(UserError):
            cheque.action_clear()
        cheque.action_present()
        cheque.action_clear()
        self.assertEqual(cheque.state, 'cleared')
        self.assertEqual(cheque.cleared_by_id, self.env.user)

    def test_cancel_blocks_cleared(self):
        cheque = self._make_incoming()
        cheque.action_register()
        cheque.action_present()
        cheque.action_clear()
        with self.assertRaises(UserError):
            cheque.action_cancel()

    def test_cancel_from_draft(self):
        cheque = self._make_incoming()
        cheque.action_cancel()
        self.assertEqual(cheque.state, 'cancelled')
        self.assertEqual(cheque.cancelled_by_id, self.env.user)

    # ---- overdue ----

    def test_is_overdue_flag(self):
        past = self.today - timedelta(days=5)
        cheque = self._make_incoming(value_date=past)
        cheque.action_register()
        cheque.invalidate_recordset()
        self.assertTrue(cheque.is_overdue)

    def test_is_overdue_search(self):
        past = self.today - timedelta(days=5)
        c1 = self._make_incoming(value_date=past)
        c1.action_register()
        c2 = self._make_incoming(
            cheque_number='CUST-99999',
            value_date=self.today + timedelta(days=10),
        )
        c2.action_register()
        overdue_ids = self.env['eh.cheque'].search([
            ('is_overdue', '=', True),
        ]).ids
        self.assertIn(c1.id, overdue_ids)
        self.assertNotIn(c2.id, overdue_ids)

    # ---- cron ----

    def test_cron_auto_present_picks_due_cheques(self):
        past = self.today - timedelta(days=1)
        cheque = self._make_incoming(value_date=past)
        cheque.action_register()
        future_cheque = self._make_incoming(
            cheque_number='FUT-1',
            value_date=self.today + timedelta(days=10),
        )
        future_cheque.action_register()

        self.env['eh.cheque']._cron_auto_present()

        cheque.invalidate_recordset()
        future_cheque.invalidate_recordset()
        self.assertEqual(cheque.state, 'presented')
        self.assertEqual(future_cheque.state, 'registered')
