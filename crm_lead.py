from odoo import models, fields, api
import base64


class PropertyFloorPlan(models.Model):
    _name = "property.floorplan"
    _description = "Property Floor Plan"

    name = fields.Char(string="Floor Plan Name")
    image = fields.Image(string="Floor Plan", max_width=1920, max_height=1080)
    file_size = fields.Char(string="File Size", compute="_compute_file_size", store=True)
    property_id = fields.Many2one(comodel_name="property.detail", string="Property")

    @api.depends("image")
    def _compute_file_size(self):
        for record in self:
            if record.image:
                record.file_size = f"{round(len(record.image) / 1024, 2)} Kb"
            else:
                record.file_size = ""
