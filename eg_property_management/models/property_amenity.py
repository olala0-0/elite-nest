from odoo import models, fields


class PropertyAmenity(models.Model):
    _name = "property.amenity"
    _description = "Property Amenity"

    name = fields.Char(string="Amenity")
    icon = fields.Binary(string="Icon")
    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    project_id = fields.Many2one(comodel_name="property.project", string="Project")
    sub_project_id = fields.Many2one(comodel_name="property.sub.project", string="Sub Project")
