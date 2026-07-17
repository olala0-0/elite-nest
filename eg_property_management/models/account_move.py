from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    # Define the custom fields to link to your property management system
    property_id = fields.Many2one(
        comodel_name="property.detail", 
        string="Property / Unit"
    )
    rent_contract_id = fields.Many2one(
        comodel_name="rent.contract", 
        string="Rent Contract"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """ Automatically detect and link Property & Rent Contract when 
        creating an invoice from a Rent Contract screen, OR when uploading/importing
        invoices containing a Customer/Tenant. """
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        # Scenario A: Invoice created directly from a Rent Contract screen
        if active_model == 'rent.contract' and active_id:
            contract = self.env['rent.contract'].browse(active_id)
            if contract.exists():
                for vals in vals_list:
                    if not vals.get('rent_contract_id'):
                        vals['rent_contract_id'] = contract.id
                    if not vals.get('property_id') and contract.property_id:
                        vals['property_id'] = contract.property_id.id

        # Scenario B: Invoices imported (CSV) or uploaded (PDF/OCR)
        else:
            for vals in vals_list:
                partner_id = vals.get('partner_id')
                if partner_id and not vals.get('rent_contract_id'):
                    # Search for an active running contract first
                    contract = self.env['rent.contract'].sudo().search([
                        ('partner_id', '=', partner_id),
                        ('state', '=', 'running')
                    ], limit=1)
                    # Fallback to any available contract for this tenant if none is currently 'running'
                    if not contract:
                        contract = self.env['rent.contract'].sudo().search([
                            ('partner_id', '=', partner_id)
                        ], limit=1)
                    
                    if contract:
                        vals['rent_contract_id'] = contract.id
                        if not vals.get('property_id') and contract.property_id:
                            vals['property_id'] = contract.property_id.id

        return super(AccountMove, self).create(vals_list)

    @api.onchange('partner_id')
    def _onchange_partner_id_set_contract_property(self):
        """ Auto-populate Rent Contract and Property on the screen when 
        manually selecting or editing a Customer on an invoice form. """
        if self.partner_id:
            contract = self.env['rent.contract'].search([
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'running')
            ], limit=1)
            if not contract:
                contract = self.env['rent.contract'].search([
                    ('partner_id', '=', self.partner_id.id)
                ], limit=1)
            
            if contract:
                self.rent_contract_id = contract.id
                if contract.property_id:
                    self.property_id = contract.property_id.id
        else:
            self.rent_contract_id = False
            self.property_id = False
