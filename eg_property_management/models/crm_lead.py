from odoo import models, fields


class CrmLead(models.Model):
    _inherit = "crm.lead"

    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    
    def action_create_rent_contract(self):
        self.ensure_one()

        if not self.property_id:
            raise UserError("Please select a Property before creating a Rent Contract.")
        if not self.partner_id:
            raise UserError("Please set a Customer on the opportunity before creating a Rent Contract.")
        if self.property_id.property_for != 'rent':
            raise UserError("The selected Property is not marked as available For Rent.")

        return {
            'name': 'Create Rent Contract',
            'type': 'ir.actions.act_window',
            'res_model': 'rent.contract',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_property_id': self.property_id.id,
                'default_tenant_id': self.partner_id.id,
                'default_landlord_id': self.property_id.landlord_id.id,
                'default_lead_id': self.id,
            },
        }
