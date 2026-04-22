from odoo import fields, models


class PropertySection(models.Model):
    _name = "property.section"
    _description = "Property Section"

    name = fields.Char(string='Name')
