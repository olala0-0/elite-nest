from odoo import models, fields


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    property_id = fields.Many2one(comodel_name='property.detail', string="Property")
    ticket_id = fields.Many2one(comodel_name='helpdesk.ticket', string="Source Helpdesk Ticket", readonly=True)
