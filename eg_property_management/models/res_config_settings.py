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
