from odoo import models, fields, api


class SignTemplate(models.Model):
    _inherit = "sign.template"

    def action_open_pdf_editor(self):
        """Open the PDF editor wizard for this template, pre-loaded with
        the current attachment content."""
        self.ensure_one()
        wizard = self.env["sign.pdf.edit.wizard"].create({
            "template_id": self.id,
            "page_count": self._get_page_count(),
        })
        return {
            "type": "ir.actions.act_window",
            "name": "Edit PDF",
            "res_model": "sign.pdf.edit.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def _get_main_attachment(self):
        """The Sign PDF is stored as a standalone ir.attachment linked to
        this template via res_model/res_id - there is no direct
        attachment_id field on sign.template in Odoo 19."""
        self.ensure_one()
        return self.env["ir.attachment"].search([
            ("res_model", "=", "sign.template"),
            ("res_id", "=", self.id),
            ("mimetype", "=", "application/pdf"),
        ], order="id desc", limit=1)

    def _get_page_count(self):
        self.ensure_one()
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return 0
        attachment = self._get_main_attachment()
        if not attachment or not attachment.datas:
            return 0
        import base64
        pdf_bytes = base64.b64decode(attachment.datas)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = doc.page_count
        doc.close()
        return count
