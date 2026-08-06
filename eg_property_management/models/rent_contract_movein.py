from odoo import fields, models


class RentContractMoveIn(models.Model):
    _name = 'rent.contract.movein'
    _description = 'Rent Contract Move-In'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    rent_contract_id = fields.Many2one(comodel_name='rent.contract', string='Rent Contract',
                                       required=True, ondelete='cascade')
    property_id = fields.Many2one(related='rent_contract_id.property_id', string='Property',
                                  store=True, readonly=True)
    tenant_id = fields.Many2one(related='rent_contract_id.tenant_id', string='Tenant',
                                store=True, readonly=True)
    company_id = fields.Many2one(related='rent_contract_id.company_id', string='Company',
                                 store=True, readonly=True)

    pre_move_in_inspection_id = fields.Many2one(
        comodel_name='property.inspection', string='Pre-Move-In Inspection', copy=False,
        domain="[('inspection_type', '=', 'move_in')]")

    contract_signed_date = fields.Date(string='Contract Signed On')

    invoice_expected_amount = fields.Monetary(related='rent_contract_id.invoice_expected_amount',
                                              string='Expected Amount', readonly=True)
    invoice_paid_amount = fields.Monetary(related='rent_contract_id.invoice_paid_amount',
                                          string='Paid Amount', readonly=True)
    currency_id = fields.Many2one(related='rent_contract_id.currency_id', string='Currency',
                                  store=True, readonly=True)

    move_in_permit_issued = fields.Boolean(string='Move-In Permit Issued', readonly=True)
    move_in_permit_date = fields.Date(string='Move-In Permit Date', readonly=True)

    welcome_email_sent = fields.Boolean(string='Welcome Email Sent', readonly=True)
    welcome_email_date = fields.Date(string='Welcome Email Date', readonly=True)

    handover_date = fields.Date(string='Property Handover Date')

    state = fields.Selection(
        [('draft', 'Draft'), ('inspection_done', 'Inspection Done'), ('contract_signed', 'Contract Signed'),
         ('payment_verified', 'Payment Verified'), ('handed_over', 'Handed Over'), ('settled', 'Settled')],
        string='Status', default='draft', tracking=True)

    def action_create_or_open_inspection(self):
        """Create the Pre-Move-In inspection on first click, otherwise just
        open the existing one - so the button always does the right thing
        regardless of where the process currently stands."""
        self.ensure_one()
        if not self.pre_move_in_inspection_id:
            self.pre_move_in_inspection_id = self.env['property.inspection'].create({
                'rent_contract_id': self.rent_contract_id.id,
                'property_id': self.property_id.id,
                'tenant_id': self.tenant_id.id,
                'inspection_type': 'move_in',
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'property.inspection',
            'res_id': self.pre_move_in_inspection_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_mark_inspection_done(self):
        for rec in self:
            rec.state = 'inspection_done'

    def action_mark_contract_signed(self):
        for rec in self:
            rec.write({'state': 'contract_signed', 'contract_signed_date': fields.Date.today()})

    def action_issue_move_in_permit(self):
        for rec in self:
            rec.write({'move_in_permit_issued': True, 'move_in_permit_date': fields.Date.today()})

    def action_mark_welcome_email_sent(self):
        for rec in self:
            rec.write({'welcome_email_sent': True, 'welcome_email_date': fields.Date.today()})

    def action_mark_payment_verified(self):
        """Manual checkpoint: Finance looks at invoice_paid_amount /
        invoice_expected_amount (shown on the form) and confirms. Those two
        fields stay the single source of truth on rent.contract - this
        button only records that a human reviewed them, it never computes
        or stores a payment figure of its own."""
        for rec in self:
            rec.state = 'payment_verified'

    def action_mark_handed_over(self):
        for rec in self:
            rec.write({'state': 'handed_over', 'handover_date': fields.Date.today()})

    def action_settle(self):
        for rec in self:
            rec.state = 'settled'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
