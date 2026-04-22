from odoo import models, fields, api
import base64


class PropertyImage(models.Model):
    _name = "property.image"
    _description = "Property Images"

    name = fields.Char(string="Title")
    image = fields.Image(string="Image", required=True)
    file_size = fields.Char(string="File Size")
    property_id = fields.Many2one("property.detail", string="Property", ondelete="cascade")
    project_id = fields.Many2one(comodel_name="property.project", string="Project")
    sub_project_id = fields.Many2one(comodel_name="property.sub.project", string="Sub Project")

    @api.onchange("image")
    def _onchange_file_size(self):
        for record in self:
            if record.image:
                record.file_size = f"{round(len(record.image) / 1024, 2)} Kb"
            else:
                record.file_size = ""
