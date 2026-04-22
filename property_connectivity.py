from odoo import fields, models


class PropertySpecification(models.Model):
    _name = "property.specification"
    _description = "Property Specification"

    name = fields.Char(string="Title")
    description = fields.Text(string="Description")
    image = fields.Binary(string="Image", attachment=True)
    is_premium = fields.Boolean(string="Premium")
    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    project_id = fields.Many2one(comodel_name="property.project", string="Project")
    sub_project_id = fields.Many2one(comodel_name="property.sub.project", string="Sub Project")
