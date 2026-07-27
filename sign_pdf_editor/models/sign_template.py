from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
        """The Sign PDF is usually stored as a standalone ir.attachment
        linked to this template via res_model/res_id."""
        self.ensure_one()
        return self.env["ir.attachment"].search([
            ("res_model", "=", "sign.template"),
            ("res_id", "=", self.id),
        ], order="id desc", limit=1)

    def _get_pdf_field_name(self):
        """Fallback: some Sign versions/forks store the PDF directly as a
        Binary field on sign.template itself rather than via ir.attachment.
        Introspect for a plausible field name if the attachment lookup
        comes up empty."""
        self.ensure_one()
        candidates = ["datas", "pdf_file", "document", "template_data",
                      "sign_template_data", "attachment_datas"]
        fields_info = self.fields_get()
        for name in candidates:
            if name in fields_info and fields_info[name]["type"] == "binary":
                return name
        # last resort: any binary field at all on the model
        for name, info in fields_info.items():
            if info["type"] == "binary":
                return name
        return None

    def _get_pdf_datas(self):
        """Return the base64 PDF content, wherever it actually lives."""
        self.ensure_one()
        attachment = self._get_main_attachment()
        if attachment and attachment.datas:
            return attachment.datas
        field_name = self._get_pdf_field_name()
        if field_name:
            return self[field_name]
        return False

    def _set_pdf_datas(self, new_data):
        """Write updated base64 PDF content back to wherever it lives."""
        self.ensure_one()
        attachment = self._get_main_attachment()
        if attachment:
            attachment.write({"datas": new_data})
            return
        field_name = self._get_pdf_field_name()
        if field_name:
            self.write({field_name: new_data})
            return
        raise UserError(_("Could not find where this template's PDF is stored."))

    def _get_page_count(self):
        self.ensure_one()
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return 0
        datas = self._get_pdf_datas()
        if not datas:
            return 0
        import base64
        pdf_bytes = base64.b64decode(datas)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = doc.page_count
        doc.close()
        return count
