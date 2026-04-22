from odoo import models, fields


class PropertyConnectivity(models.Model):
    _name = "property.connectivity"
    _description = "Nearby Connectivity"

    name = fields.Char(string="Connectivity Name")
    icon = fields.Image(string="Icon", max_width=128, max_height=128)
    description = fields.Text(string="Description")
    distance = fields.Float(string="Distance (KM)")
    property_id = fields.Many2one(comodel_name="property.detail", string="Property", ondelete="cascade")
    project_id = fields.Many2one(comodel_name="property.project", string="Project")
    sub_project_id = fields.Many2one(comodel_name="property.sub.project", string="Sub Project")
