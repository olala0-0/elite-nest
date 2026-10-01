from odoo import models, fields
from odoo.tools import html2plaintext


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    property_id = fields.Many2one(
        comodel_name='property.detail',
        string="Property"
    )

    ticket_id = fields.Many2one(
        comodel_name='helpdesk.ticket',
        string="Source Helpdesk Ticket",
        readonly=True
    )

    def export_data(self, fields_to_export):
        result = super().export_data(fields_to_export)

        # Clean HTML from Description when exporting
        if 'description' in fields_to_export:
            description_index = fields_to_export.index('description')

            for row in result.get('datas', []):
                if description_index < len(row):
                    row[description_index] = html2plaintext(
                        row[description_index] or ''
                    )

        return result
