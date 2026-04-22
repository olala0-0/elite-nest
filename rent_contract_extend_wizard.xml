from odoo import models, fields
from odoo.exceptions import UserError


class RentContractExtendWizard(models.TransientModel):
    _name = 'rent.contract.extend.wizard'
    _description = 'Extend Rent Contract'

    new_end_date = fields.Date(string="New End Date", required=True)

    def action_extend_contract(self):
        self.ensure_one()
        rent_contract_ids = self.env['rent.contract'].browse(self.env.context['active_ids'])

        if self.new_end_date <= rent_contract_ids.end_date:
            raise UserError("New end date must be after current end date.")

        rent_contract_ids.end_date = self.new_end_date
        rent_contract_ids.state = 'running'

        rent_contract_ids.action_create_invoice()
