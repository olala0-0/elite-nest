import io
import base64
from odoo import models, fields
import xlsxwriter


class RentContractFulkReport(models.TransientModel):
    _name = "rent.contract.full.report"
    _description = "Rent Contract Full XLS Report"

    rent_contract_ids = fields.Many2many(comodel_name='rent.contract', string='Rent Contract')

    def action_rent_contract_full_report(self):
        if not self.rent_contract_ids:
            return

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})
        amount_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#FFF2CC', 'border': 1, 'num_format': '#,##0.00'})
        total_label_format = workbook.add_format({'bold': True, 'bg_color': '#FFF2CC', 'border': 1})

        headers = ['Reference', 'Property', 'Residential Type', 'Customer', 'Landlord', 'Broker', 'Total Area',
                   'Start Date', 'End Date', 'Payment Term', 'Rent', 'Security Deposit', 'Broker Commission',
                   'Total Amount', 'Paid Amount', 'Remaining Amount', 'Status']
        contract_groups_ids = {'All Contracts': self.rent_contract_ids,
                               'Running Contracts': self.rent_contract_ids.filtered(lambda c: c.state in ('running', 'move_out')),
                               'Terminated Contracts': self.rent_contract_ids.filtered(lambda c: c.state == 'terminate'),
                               'Expired Contracts': self.rent_contract_ids.filtered(lambda c: c.state == 'expire'), }

        for sheet_name, contracts_id in contract_groups_ids.items():
            if not contracts_id:
                continue

            worksheet = workbook.add_worksheet(sheet_name)
            worksheet.merge_range(0, 0, 0, len(headers) - 1, f"{sheet_name}", header_format)

            for col, header in enumerate(headers):
                worksheet.write(1, col, header, header_format)

            row = 2
            for contract in contracts_id:
                data = [contract.name or '',
                        contract.property_id.name or '',
                        contract.residential_type_id.name or contract.type or '',
                        contract.tenant_id.name or '',
                        contract.landlord_id.name or '',
                        contract.broker_id.name or '',
                        f"{contract.total_area or 0} m²",
                        contract.start_date.strftime('%d/%m/%Y') if contract.start_date else '',
                        contract.end_date.strftime('%d/%m/%Y') if contract.end_date else '',
                        contract.payment_term or '',
                        contract.rent or 0.0,
                        contract.deposit or 0.0,
                        contract.broker_commission or 0.0,
                        contract.invoice_expected_amount or 0.0,
                        contract.invoice_paid_amount or 0.0,
                        contract.invoice_due_amount or 0.0,
                        dict(contract._fields['state'].selection).get(contract.state, 'Unknown'), ]

                for col, value in enumerate(data):
                    if col in [10, 11, 12, 13, 14, 15]:
                        worksheet.write(row, col, value, amount_format)
                    else:
                        worksheet.write(row, col, value)
                row += 1

            paid_total = sum(float(c.invoice_paid_amount or 0.0) for c in contracts_id)
            due_total = sum(float(c.invoice_due_amount or 0.0) for c in contracts_id)
            total_amount = paid_total + due_total

            worksheet.write(row, 12, "Totals", total_label_format)
            worksheet.write(row, 13, total_amount, total_format)
            worksheet.write(row, 14, paid_total, total_format)
            worksheet.write(row, 15, due_total, total_format)

        workbook.close()
        output.seek(0)

        data = base64.b64encode(output.read())
        attachment = self.env['ir.attachment'].create({
            'name': 'Rent_Contracts_Full_Report.xlsx',
            'type': 'binary',
            'datas': data,
            'store_fname': 'Rent_Contracts_Full_Report.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
