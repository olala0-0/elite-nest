from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

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
