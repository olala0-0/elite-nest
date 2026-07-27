from odoo import models, fields, api


class SignTemplate(models.Model):
    _inherit = "sign.template"

    def action_open_pdf_editor(self):
        """Open the PDF editor wizard for this template, pre-loaded with
        the current attachment content."""
        self.ensure_one()
        attachment = self.attachment_id
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

    def _get_page_count(self):
        self.ensure_one()
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return 0
        if not self.attachment_id or not self.attachment_id.datas:
            return 0
        import base64
        pdf_bytes = base64.b64decode(self.attachment_id.datas)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = doc.page_count
        doc.close()
        return count
