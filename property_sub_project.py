from odoo import fields, models
from random import randint


class PropertyTag(models.Model):
    _name = "property.tag"
    _description = "Property Tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color)
