from odoo import fields, models


class PropertyUtilityService(models.Model):
    _name = "property.service"
    _description = "Property Service"

    name = fields.Char(string="Service Name", required=True)
    code = fields.Char(string="Code", required=True)
    active = fields.Boolean(string="Active", default=True)
