from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    property_id = fields.Many2one(
        comodel_name="property.detail",
        string="Property / Unit",
        check_company=False,
    )
    rent_contract_id = fields.Many2one(
        comodel_name="rent.contract",
        string="Rent Contract",
        check_company=False,
    )

    def _check_company(self, fnames=None):
        """Allow GHD invoices to link to Elite Nest contracts and properties
        without triggering cross-company validation errors."""
        if fnames is None:
            fnames = self._fields.keys()
        excluded = {'property_id', 'rent_contract_id', 'contract_id'}
        filtered_fnames = [f for f in fnames if f not in excluded]
        return super(AccountMove, self)._check_company(fnames=filtered_fnames)

    @api.model_create_multi
    def create(self, vals_list):
        """ Automatically detect and link Property & Rent Contract when 
        creating an invoice from a Rent Contract screen, OR when uploading/importing
        invoices containing a Customer/Tenant. """
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        # Scenario A: Created directly from a Rent Contract screen / button action
        if active_model == 'rent.contract' and active_id:
            contract = self.env['rent.contract'].sudo().browse(active_id)
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
                        ('state', 'in', ('running', 'move_out'))
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
        if self.env.context.get('skip_sync_installment') or self.env.context.get('active_model') == 'rent.contract':
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
                            'company_id': move.company_id.id,
                        })
                else:
                    invoice_date = move.invoice_date or fields.Date.today()
                    contract = move.rent_contract_id.sudo()
                    is_scheduled_rent = invoice_date in contract._get_pending_rent_due_dates()
                    payment_type = 'rent' if is_scheduled_rent else 'other'
                    first_line = move.invoice_line_ids[:1]
                    default_description = (
                        f"Rent payment for {move.property_id.name or 'Unit'}" if is_scheduled_rent
                        else f"Manual charge for {move.property_id.name or 'Unit'}"
                    )
                    self.env['rent.installment'].with_company(move.company_id).sudo().create({
                        'rent_contract_id': move.rent_contract_id.id,
                        'company_id': move.company_id.id,
                        'product_id': first_line.product_id.id if first_line and first_line.product_id else False,
                        'invoice_date': invoice_date,
                        'payment_type': payment_type,
                        'description': first_line.name if first_line else default_description,
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
            contract = self.env['rent.contract'].sudo().search([
                ('tenant_id', '=', self.partner_id.id),
                ('state', 'in', ('running', 'move_out'))
            ], limit=1)
            if not contract:
                contract = self.env['rent.contract'].sudo().search([
                    ('tenant_id', '=', self.partner_id.id)
                ], limit=1)

            if contract:
                self.rent_contract_id = contract.id
                if contract.property_id:
                    self.property_id = contract.property_id.id
        else:
            self.rent_contract_id = False
            self.property_id = False


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _check_company(self, fnames=None):
        """Allow cross-company links to property/contract fields on invoice lines."""
        if fnames is None:
            fnames = self._fields.keys()
        excluded = {'property_id', 'rent_contract_id', 'contract_id'}
        filtered_fnames = [f for f in fnames if f not in excluded]
        return super(AccountMoveLine, self)._check_company(fnames=filtered_fnames)
