from datetime import timedelta
from odoo import models, fields
from odoo.exceptions import UserError


class RentContractExtendWizard(models.TransientModel):
    _name = 'rent.contract.extend.wizard'
    _description = 'Extend / Renew Rent Contract'

    contract_id = fields.Many2one(
        comodel_name='rent.contract',
        string="Original Contract",
        default=lambda self: self.env.context.get('active_id'),
        readonly=True,
    )
    new_start_date = fields.Date(
        string="New Start Date",
        required=True,
    )
    new_end_date = fields.Date(
        string="New End Date",
        required=True,
    )
    new_rent = fields.Monetary(
        string="New Rent Amount",
        currency_field='currency_id',
        help="Leave as original rent or adjust if there is a rent revision upon renewal.",
    )
    currency_id = fields.Many2one(
        related='contract_id.currency_id',
        string="Currency",
        readonly=True,
    )

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            old_contract = self.env['rent.contract'].browse(active_id)
            res['contract_id'] = old_contract.id
            if old_contract.end_date:
                default_start = old_contract.end_date + timedelta(days=1)
                res['new_start_date'] = default_start
                # Default end date to 1 year minus 1 day later
                try:
                    from dateutil.relativedelta import relativedelta
                    res['new_end_date'] = default_start + relativedelta(years=1) - timedelta(days=1)
                except Exception:
                    res['new_end_date'] = default_start + timedelta(days=364)
            res['new_rent'] = old_contract.rent
        return res

    def action_extend_contract(self):
        self.ensure_one()
        active_id = self.env.context.get('active_id')
        old_contract = self.contract_id or self.env['rent.contract'].browse(active_id)

        if not old_contract:
            raise UserError("No contract found to extend.")

        if self.new_end_date <= self.new_start_date:
            raise UserError("New End Date must be after New Start Date.")

        # Check if already renewed
        existing_renewal = self.env['rent.contract'].sudo().search([
            ('previous_contract_id', '=', old_contract.id)
        ], limit=1)
        if existing_renewal:
            raise UserError(f"This contract has already been renewed as {existing_renewal.name}.")

        # Prepare values for new contract (Option A: Archive & Create New)
        new_contract_vals = {
            'property_id': old_contract.property_id.id,
            'tenant_id': old_contract.tenant_id.id,
            'landlord_id': old_contract.landlord_id.id,
            'company_id': old_contract.company_id.id,
            'currency_id': old_contract.currency_id.id,
            'property_type': old_contract.property_type,
            'user_id': old_contract.user_id.id,
            'payment_term_id': old_contract.payment_term_id.id,
            'contract_type': old_contract.contract_type,
            'start_date': self.new_start_date,
            'end_date': self.new_end_date,
            'invoice_start_date': self.new_start_date,
            'rent': self.new_rent if self.new_rent else old_contract.rent,
            'deposit': old_contract.deposit,
            'ejari_fee': old_contract.ejari_fee,
            'admin_charge': old_contract.admin_charge,
            'commission': old_contract.commission,
            'parking_fee': old_contract.parking_fee,
            'total_maintenance': old_contract.total_maintenance,
            'maintenance_type': old_contract.maintenance_type,
            'charge_type': old_contract.charge_type,
            'penalty_type': old_contract.penalty_type,
            'penalty_value': old_contract.penalty_value,
            'penalty_grace_days': old_contract.penalty_grace_days,
            'penalty_product_id': old_contract.penalty_product_id.id if old_contract.penalty_product_id else False,
            'tax_rate': old_contract.tax_rate,
            'broker_id': old_contract.broker_id.id if old_contract.broker_id else False,
            'broker_commission': old_contract.broker_commission,
            'agreement': old_contract.agreement,
            'terms_conditions': old_contract.terms_conditions,
            'total_area': old_contract.total_area,
            'usable_area': old_contract.usable_area,
            'street': old_contract.street,
            'street2': old_contract.street2,
            'city': old_contract.city,
            'state_id': old_contract.state_id.id if old_contract.state_id else False,
            'zip': old_contract.zip,
            'country_id': old_contract.country_id.id if old_contract.country_id else False,
            'region_id': old_contract.region_id.id if old_contract.region_id else False,
            'previous_contract_id': old_contract.id,
            'state': 'draft',
        }

        # Copy utility services
        utility_lines = []
        for util in old_contract.utility_service_ids:
            utility_lines.append((0, 0, {
                'service_type_id': util.service_type_id.id if hasattr(util, 'service_type_id') and util.service_type_id else False,
                'cost': util.cost,
            }))
        if utility_lines:
            new_contract_vals['utility_service_ids'] = utility_lines

        new_contract = self.env['rent.contract'].create(new_contract_vals)

        # Log renewal history on chatter of both old and new contracts
        old_contract.message_post(
            body=(
                f"<b>Contract Renewed:</b> This expired contract was renewed for the period "
                f"<b>{self.new_start_date}</b> to <b>{self.new_end_date}</b>. "
                f"New contract created: <a href='#id={new_contract.id}&model=rent.contract'>{new_contract.name}</a>."
            ),
            subtype_xmlid='mail.mt_comment'
        )

        new_contract.message_post(
            body=(
                f"<b>Renewed From:</b> Created as renewal of expired contract "
                f"<a href='#id={old_contract.id}&model=rent.contract'>{old_contract.name}</a> "
                f"(previous period: {old_contract.start_date} to {old_contract.end_date}, rent: {old_contract.rent} {old_contract.currency_id.symbol or ''})."
            ),
            subtype_xmlid='mail.mt_comment'
        )

        # Return action to open the newly created contract
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renewed Rent Contract',
            'res_model': 'rent.contract',
            'res_id': new_contract.id,
            'view_mode': 'form',
            'target': 'current',
        }