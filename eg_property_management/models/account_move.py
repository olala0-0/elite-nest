from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

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

        # Scenario A: Created directly from a Rent Contract screen / button action
        if active_model == 'rent.contract' and active_id:
            contract = self.env['rent.contract'].browse(active_id)
            if contract.exists():
                for vals in vals_list:
                    if not vals.get('rent_contract_id'):
                        vals['rent_contract_id'] = contract.id
                    if not vals.get('property_id') and contract.property_id:
                        vals['property_id'] = contract.property_id.id

        # Scenario B: Uploaded, imported, or created via OCR/API/CSV (without active contract screen context)
        else:
            for vals in vals_list:
                partner_id = vals.get('partner_id')
                if partner_id and not vals.get('rent_contract_id'):
                    # Search for an active running contract first using tenant_id
                    contract = self.env['rent.contract'].sudo().search([
                        ('tenant_id', '=', partner_id),
                        ('state', '=', 'running')
                    ], limit=1)
                    # Fallback to any contract for this tenant if none is currently 'running'
                    if not contract:
                        contract = self.env['rent.contract'].sudo().search([
                            ('tenant_id', '=', partner_id)
                        ], limit=1)
                    
                    if contract:
                        vals['rent_contract_id'] = contract.id
                        if not vals.get('property_id') and contract.property_id:
                            vals['property_id'] = contract.property_id.id

        moves = super(AccountMove, self).create(vals_list)
        # Synchronize rent installments for newly created manual customer invoices
        moves._sync_rent_installments()
        return moves

    def write(self, vals):
        """ Trigger installment synchronization whenever crucial invoice metrics are edited. """
        res = super(AccountMove, self).write(vals)
        if any(field in vals for field in ['rent_contract_id', 'invoice_line_ids', 'invoice_date', 'currency_id', 'state', 'partner_id']):
            self._sync_rent_installments()
        return res

    def _sync_rent_installments(self):
        """ Automatically creates, edits, or deletes 'rent.installment' lines in the background
        to ensure manual Accounting invoices reflect flawlessly inside Rent Contract master sheets. """
        # Skip automatic synchronization if we are already in the context of the Rent Contract's action_create_invoice wizard
        if self.env.context.get('active_model') == 'rent.contract':
            return
        
        for move in self:
            if move.move_type == 'out_invoice' and move.rent_contract_id:
                # Sum the price subtotal from lines to bypass uncomputed draft totals
                amount = sum(move.invoice_line_ids.mapped('price_subtotal'))
                
                existing_installments = self.env['rent.installment'].sudo().search([
                    ('invoice_id', '=', move.id)
                ])
                
                if existing_installments:
                    # Update the existing installment entry with the modified invoice details
                    if len(existing_installments) == 1:
                        existing_installments.sudo().write({
                            'amount': amount,
                            'invoice_date': move.invoice_date or fields.Date.today(),
                            'currency_id': move.currency_id.id,
                        })
                else:
                    # Automatically generate a new installment ledger line for this manual invoice
                    self.env['rent.installment'].sudo().create({
                        'rent_contract_id': move.rent_contract_id.id,
                        'invoice_date': move.invoice_date or fields.Date.today(),
                        'payment_type': 'rent',
                        'description': move.invoice_line_ids[0].name if move.invoice_line_ids else f"Rent payment for {move.property_id.name or 'Unit'}",
                        'amount': amount,
                        'currency_id': move.currency_id.id,
                        'invoice_id': move.id,
                    })
            else:
                # If the invoice is deleted, draft canceled, or contract unlinked, clean up the ledger entry
                installments = self.env['rent.installment'].sudo().search([
                    ('invoice_id', '=', move.id)
                ])
                if installments:
                    installments.sudo().unlink()

    @api.onchange('partner_id')
    def _onchange_partner_id_set_contract_property(self):
        """ Auto-populate Rent Contract and Property on the screen when 
        manually selecting or editing a Customer on an invoice form. """
        if self.partner_id:
            # Search active running contracts matching selected customer
            contract = self.env['rent.contract'].search([
                ('tenant_id', '=', self.partner_id.id),
                ('state', '=', 'running')
            ], limit=1)
            if not contract:
                contract = self.env['rent.contract'].search([
                    ('tenant_id', '=', self.partner_id.id)
                ], limit=1)
            
            if contract:
                self.rent_contract_id = contract.id
                if contract.property_id:
                    self.property_id = contract.property_id.id
        else:
            self.rent_contract_id = False
            self.property_id = False
