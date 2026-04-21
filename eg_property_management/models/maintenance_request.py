from odoo import models, fields


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    property_id = fields.Many2one(comodel_name='property.detail', string="Property")
