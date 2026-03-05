import io
import base64
from odoo import models, fields
import xlsxwriter


class RentContractReport(models.TransientModel):
    _name = "rent.contract.report"
    _description = "Rent Contract Landlord XLS Report"

    landlord_id = fields.Many2one(comodel_name="res.partner", string="Landlord")

    def action_rent_contract_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})
        amount_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        landlord_name = self.landlord_id.name or 'All Landlords'

        headers = ['Reference', 'Tenant', 'Property', 'Invoice Reference', 'Payment Term', 'Amount', 'Payment Status',
                   'Contract Status']

        contract_id = self.env['rent.contract'].search([('landlord_id', '=', self.landlord_id.id)])

        if not contract_id:
            raise UserError("No contracts found for the selected landlord.")

        contract_groups = {'All Contracts': contract_id,
                           'Paid Contracts': contract_id.filtered(lambda c: all(
                               inv.payment_state == 'paid' for inv in c.rent_installment_ids.mapped('invoice_id'))),
                           'Partial Paid Contracts': contract_id.filtered(
                               lambda c: c.rent_installment_ids and not (all(
                                   inv.payment_state == 'paid' for inv in c.rent_installment_ids.mapped('invoice_id'))
                                                                         or all(
                                           inv.payment_state == 'not_paid' for inv in
                                           c.rent_installment_ids.mapped('invoice_id')))),
                           'Not Paid Contracts': contract_id.filtered(
                               lambda c: all(inv.payment_state == 'not_paid' for inv in
                                             c.rent_installment_ids.mapped('invoice_id')))
                           }

        for sheet_name, contract_id in contract_groups.items():
            if contract_id:
                worksheet = workbook.add_worksheet(sheet_name)
                worksheet.merge_range(0, 0, 0, len(headers) - 1, f"RENT INFORMATION - {landlord_name}", header_format)
                for col, header in enumerate(headers):
                    worksheet.write(1, col, header, header_format)

                row = 2
                for contract in contract_id:
                    invoice_refs = contract.rent_installment_ids.mapped('invoice_id.name')
                    invoice_refs_str = ', '.join(filter(None, invoice_refs)) or 'N/A'

                    all_invoices = contract.rent_installment_ids.mapped('invoice_id')
                    if all(inv.payment_state == 'paid' for inv in all_invoices):
                        overall_payment_status = 'Paid'
                    elif all(inv.payment_state == 'not_paid' for inv in all_invoices):
                        overall_payment_status = 'Not Paid'
                    else:
                        overall_payment_status = 'Partial Paid'
                    data = [contract.name or '',
                            contract.tenant_id.name or '',
                            contract.property_id.name or '',
                            invoice_refs_str,
                            contract.payment_term or '',
                            contract.rent or 0.0,
                            overall_payment_status,
                            dict(contract._fields['state'].selection).get(contract.state, 'Unknown')]

                    for col, value in enumerate(data):
                        if col == 5:
                            worksheet.write(row, col, value, amount_format)
                        else:
                            worksheet.write(row, col, value)
                    row += 1

        workbook.close()
        output.seek(0)

        data = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({
            'name': 'Rent_Contracts_Report.xlsx',
            'type': 'binary',
            'datas': data,
            'store_fname': 'Rent_Contracts_Landlord_Report.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment_id.id}?download=true',
            'target': 'self',
        }
