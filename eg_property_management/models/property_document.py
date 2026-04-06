from odoo import models, fields


class PropertyDocument(models.Model):
    _name = "property.document"
    _description = "Property Document"

    name = fields.Char(string="Document Name", )
    document_file = fields.Binary(string="File", attachment=True)
    document_filename = fields.Char(string="Filename")
    document_date = fields.Date(string="Date", default=fields.Date.today)

    property_id = fields.Many2one(comodel_name="property.detail", string="Property", invisible=True)
    sub_project_id = fields.Many2one(comodel_name="property.sub.project", string="Sub Project", invisible=True,
                                     related='property_id.sub_project_id')
    project_id = fields.Many2one(comodel_name="property.project", string="Project", invisible=True,
                                 related='sub_project_id.project_id')
    rent_contract_id = fields.Many2one(comodel_name="rent.contract", string="Rent Contract",invisible=True)
