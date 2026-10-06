from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    renewal_notice_months = fields.Selection(
        [('1', '1 Month'), ('2', '2 Months'), ('3', '3 Months')],
        string="Renewal Notice Period",
        config_parameter="eg_property_management.renewal_notice_months",
        default='3',
    )
    rent_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Rent Invoice Product",
        config_parameter="eg_property_management.rent_invoice_product_id",
    )
    rent_invoice_description = fields.Char(
        string="Rent Invoice Description",
        config_parameter="eg_property_management.rent_invoice_description",
    )
    deposit_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Deposit Invoice Product",
        config_parameter="eg_property_management.deposit_invoice_product_id",
    )
    deposit_invoice_description = fields.Char(
        string="Deposit Invoice Description",
        config_parameter="eg_property_management.deposit_invoice_description",
    )
    maintenance_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Maintenance Invoice Product",
        config_parameter="eg_property_management.maintenance_invoice_product_id",
    )
    maintenance_invoice_description = fields.Char(
        string="Maintenance Invoice Description",
        config_parameter="eg_property_management.maintenance_invoice_description",
    )
    penalty_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Penalty Invoice Product",
        config_parameter="eg_property_management.penalty_invoice_product_id",
    )
    penalty_invoice_description = fields.Char(
        string="Penalty Invoice Description",
        config_parameter="eg_property_management.penalty_invoice_description",
    )
    ejari_fee_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Ejari Fee Invoice Product",
        config_parameter="eg_property_management.ejari_fee_invoice_product_id",
    )
    ejari_fee_invoice_description = fields.Char(
        string="Ejari Fee Invoice Description",
        config_parameter="eg_property_management.ejari_fee_invoice_description",
    )
    admin_charge_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Admin Charge Invoice Product",
        config_parameter="eg_property_management.admin_charge_invoice_product_id",
    )
    admin_charge_invoice_description = fields.Char(
        string="Admin Charge Invoice Description",
        config_parameter="eg_property_management.admin_charge_invoice_description",
    )
    commission_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Commission Invoice Product",
        config_parameter="eg_property_management.commission_invoice_product_id",
    )
    commission_invoice_description = fields.Char(
        string="Commission Invoice Description",
        config_parameter="eg_property_management.commission_invoice_description",
    )
    parking_fee_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Parking Fee Invoice Product",
        config_parameter="eg_property_management.parking_fee_invoice_product_id",
    )
    parking_fee_invoice_description = fields.Char(
        string="Parking Fee Invoice Description",
        config_parameter="eg_property_management.parking_fee_invoice_description",
    )
    dilapidation_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Dilapidation Invoice Product",
        config_parameter="eg_property_management.dilapidation_invoice_product_id",
    )
    dilapidation_invoice_description = fields.Char(
        string="Dilapidation Invoice Description",
        config_parameter="eg_property_management.dilapidation_invoice_description",
    )
    shortfall_rent_invoice_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Shortfall Rent Invoice Product",
        config_parameter="eg_property_management.shortfall_rent_invoice_product_id",
    )
    shortfall_rent_invoice_description = fields.Char(
        string="Shortfall Rent Invoice Description",
        config_parameter="eg_property_management.shortfall_rent_invoice_description",
    )

    contract_expiry_notice_days = fields.Integer(
        string="Expiry Notice (Days)",
        default=90,
        config_parameter="eg_property_management.contract_expiry_notice_days",
    )
    payment_reminder_min_days = fields.Integer(
        string="Payment Reminder Min Days",
        default=10,
        config_parameter="eg_property_management.payment_reminder_min_days",
    )
    payment_reminder_max_days = fields.Integer(
        string="Payment Reminder Max Days",
        default=15,
        config_parameter="eg_property_management.payment_reminder_max_days",
    )
    finance_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Finance Notification Users",
        relation="res_config_settings_finance_users_rel",
    )

    def set_values(self):
        super().set_values()
        param = self.env['ir.config_parameter'].sudo()
        param.set_param(
            'eg_property_management.finance_user_ids',
            ','.join(map(str, self.finance_user_ids.ids))
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo()
        finance_ids_str = param.get_param('eg_property_management.finance_user_ids', '')
        if finance_ids_str:
            user_ids = [int(x) for x in finance_ids_str.split(',') if x.strip().isdigit()]
            res['finance_user_ids'] = [(6, 0, user_ids)]
        return res
