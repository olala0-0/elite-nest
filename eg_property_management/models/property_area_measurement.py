from odoo import models, fields, api


class PropertyAreaMeasurement(models.Model):
    _name = "property.area.measurement"
    _description = "Property Area Measurement"

    property_id = fields.Many2one(comodel_name="property.detail", string="Property")

    section_id = fields.Many2one(comodel_name='property.section', string="Section")
    no_of_unit = fields.Integer(string="No of Unit")
    length = fields.Float(string="Length (ft)")
    width = fields.Float(string="Width (ft)")
    total_area = fields.Float(string="Total Area (sq.ft)", compute="_compute_total_area")

    @api.depends("length", "width", "no_of_unit")
    def _compute_total_area(self):
        for rec in self:
            rec.total_area = (rec.length * rec.width) * rec.no_of_unit
