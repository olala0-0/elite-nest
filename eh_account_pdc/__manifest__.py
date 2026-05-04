# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
 'name': "Post Dated Cheques (PDC)",
 'summary': "Cheque registers, issued and received cheque tracking, bank presentation, clearance and bounce workflow with re-bank or write-off. ",
 'description': """
Post Dated Cheque Management for Odoo 19 Community
====================================================

Track post dated cheques as first class records, not memo notes on payments.
Built for the where PDC is part of normal
trade and Odoo Community has no native handling.

Capabilities:

* Cheque books per bank journal with start and end serial numbers, current
 next cheque pointer, and remaining count.
* Issued cheques (vendor pay) and received cheques (customer collect) on
 one model with a direction flag.
* Lifecycle: draft, registered, presented (deposited at bank), cleared,
 bounced, replaced, cancelled. Each transition stamps user and timestamp.
* Cron driven auto presentation on the value date for issued cheques and
 optional auto presentation for received cheques per bank policy.
* Bounce workflow with reason lookup (insufficient funds, signature, stop
 payment, account closed, post dated, technical, other) and choice of
 re-bank with a new value date or write-off.
* Replacement chain: when a bounced cheque is replaced, the new cheque
 links to the original and the original moves to replaced state.
* Aged report by bank journal and direction. Dashboard counters for
 presented, cleared, bounced and replaced this month.
* Optional link from cheque to invoice or account.payment for downstream
 reconciliation. Cheque clearance can stamp the linked payment as
 reconciled.

Engineering principles:

* Cheques are real records. Queryable, exportable, audit ready.
* State machine guards prevent illegal transitions.
* Cheque book pointer is the source of truth for next serial. No two
 open cheques share a serial within a book.
* Bounce reasons are configurable, not hard coded enum literals.

Pairs with eh_account_collections for follow up on bounced customer
cheques and eh_account_close_workflow for period close validation that
no cheque is stuck in an inconsistent state.

Search keywords
---------------

Accounting, Full Accounting, Full Accounting for Community, Odoo 19
Community accounting, accounting suite, accounting modules, financial
reporting, period close, accounts receivable, accounts payable, journal
entries, double entry bookkeeping.


    """,
 'author': "ERP Heritage",
 'website': "https://www.erpheritage.com.au/",
 'license': 'LGPL-3',
 'category': 'Accounting/Accounting',
 'version': '19.0.1.0.2',
 'depends': [
 'eh_account_base',
 'account',
 'mail',
 ],
 'data': [
 'security/ir.model.access.csv',
 'security/eh_isolation_rules.xml',
 'data/bounce_reasons.xml',
 'data/cron.xml',
 'views/cheque_book_views.xml',
 'views/cheque_views.xml',
 'views/bounce_reason_views.xml',
 'views/res_partner_views.xml',
 'views/account_move_views.xml',
 'wizards/replace_cheque_wizard_views.xml',
 'wizards/bounce_cheque_wizard_views.xml',
 'report/cheque_register_report.xml',
 'data/menus.xml',
 ],
 'images': ['static/description/banner.png'],
 'installable': True,
 'application': False,
 'auto_install': False,
}
