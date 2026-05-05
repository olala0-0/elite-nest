# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Wizard to record a cheque bounce with reason and bank charges."""

from odoo import _, fields, models
from odoo.exceptions import UserError


class EhChequeBounceWizard(models.TransientModel):
    _name = 'eh.cheque.bounce.wizard'
    _description = "Bounce Cheque Wizard"

    cheque_id = fields.Many2one(
        'eh.cheque', required=True, readonly=True,
    )
    reason_id = fields.Many2one(
        'eh.cheque.bounce.reason', required=True, string="Reason",
    )
    bounce_charges = fields.Monetary()
    currency_id = fields.Many2one(
        related='cheque_id.currency_id', readonly=True,
    )
    notes = fields.Text()

    def action_confirm(self):
        self.ensure_one()
        if self.cheque_id.state != 'presented':
            raise UserError(_(
                "Only presented cheques can be bounced.",
            ))
        self.cheque_id._mark_bounced(
            reason=self.reason_id,
            charges=self.bounce_charges,
            notes=self.notes,
        )
        return {'type': 'ir.actions.act_window_close'}
