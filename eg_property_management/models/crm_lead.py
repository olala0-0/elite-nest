from odoo import models, fields


class CrmLead(models.Model):
    _inherit = "crm.lead"

    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
