import base64

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SignTemplate(models.Model):
    _inherit = "sign.template"

    def action_open_pdf_editor(self):
        """Open the PDF editor wizard for this template."""
        self.ensure_one()
        wizard = self.env["sign.pdf.edit.wizard"].create({
            "template_id": self.id,
            "page_count": self._get_page_count(),
            "debug_info": self._build_debug_info(),
        })
        return {
            "type": "ir.actions.act_window",
            "name": "Edit PDF",
            "res_model": "sign.pdf.edit.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    # ------------------------------------------------------------------
    # Locating the PDF - tries three known storage patterns in order
    # ------------------------------------------------------------------

    def _get_main_attachment(self):
        """Pattern 1: PDF stored as a standalone ir.attachment linked via
        res_model/res_id."""
        self.ensure_one()
        return self.env["ir.attachment"].search([
            ("res_model", "=", "sign.template"),
            ("res_id", "=", self.id),
        ], order="id desc", limit=1)

    def _get_pdf_via_relation(self):
        """Pattern 2: a Many2one field on sign.template pointing to an
        ir.attachment record."""
        self.ensure_one()
        fields_info = self.fields_get(attributes=["type", "relation"])
        candidates = [
            n for n, i in fields_info.items()
            if i.get("type") == "many2one" and i.get("relation") == "ir.attachment"
        ]
        candidates.sort(key=lambda n: (
            0 if any(k in n.lower() for k in ("attach", "pdf", "doc")) else 1
        ))
        for name in candidates:
            value = self[name]
            if value and value.datas:
                return value
        return None

    def _get_pdf_via_sign_document(self):
        """Pattern 3: sign.template links to a separate sign.document
        record (Many2one, One2many, or Many2many), and THAT record's PDF
        is stored as an ir.attachment linked via res_model='sign.document'.
        Confirmed to be the real pattern on Odoo 19 instances where
        sign.template has no direct attachment of its own."""
        self.ensure_one()
        if "sign.document" not in self.env:
            return None
        fields_info = self.fields_get(attributes=["type", "relation"])
        doc_ids = set()
        for name, info in fields_info.items():
            if info.get("relation") != "sign.document":
                continue
            if info.get("type") == "many2one":
                value = self[name]
                if value:
                    doc_ids.add(value.id)
            elif info.get("type") in ("one2many", "many2many"):
                for value in self[name]:
                    doc_ids.add(value.id)
        if not doc_ids:
            return None
        return self.env["ir.attachment"].search([
            ("res_model", "=", "sign.document"),
            ("res_id", "in", list(doc_ids)),
        ], order="id desc", limit=1)

    def _get_pdf_field_name(self):
        """Pattern 3: the PDF is a raw Binary field directly on
        sign.template."""
        self.ensure_one()
        candidates = ["datas", "pdf_file", "document", "template_data",
                      "sign_template_data", "attachment_datas"]
        fields_info = self.fields_get()
        for name in candidates:
            if name in fields_info and fields_info[name]["type"] == "binary":
                if self[name]:
                    return name
        for name, info in fields_info.items():
            if info["type"] == "binary" and self[name]:
                return name
        return None

    def _get_pdf_datas(self):
        """Return the base64 PDF content, wherever it actually lives."""
        self.ensure_one()
        attachment = self._get_main_attachment()
        if attachment and attachment.datas:
            return attachment.datas
        related = self._get_pdf_via_relation()
        if related:
            return related.datas
        via_doc = self._get_pdf_via_sign_document()
        if via_doc and via_doc.datas:
            return via_doc.datas
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
        related = self._get_pdf_via_relation()
        if related:
            related.write({"datas": new_data})
            return
        via_doc = self._get_pdf_via_sign_document()
        if via_doc:
            via_doc.write({"datas": new_data})
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
        pdf_bytes = base64.b64decode(datas)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = doc.page_count
        doc.close()
        return count

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def _build_debug_info(self):
        """Human-readable dump of where a PDF might be found on this
        record, shown in the wizard so we don't have to keep guessing."""
        self.ensure_one()
        lines = ["Template: %s (id=%s)" % (self.name, self.id), ""]

        attachments = self.env["ir.attachment"].search([
            ("res_model", "=", "sign.template"),
            ("res_id", "=", self.id),
        ])
        lines.append("ir.attachment via res_model/res_id: %s found" % len(attachments))
        for a in attachments:
            lines.append("  - id=%s name=%r mimetype=%r has_datas=%s"
                         % (a.id, a.name, a.mimetype, bool(a.datas)))

        fields_info = self.fields_get(attributes=["type", "relation"])
        binary_fields = [n for n, i in fields_info.items() if i["type"] == "binary"]
        m2o_attach_fields = [
            n for n, i in fields_info.items()
            if i["type"] == "many2one" and i.get("relation") == "ir.attachment"
        ]
        x2m_attach_fields = [
            n for n, i in fields_info.items()
            if i["type"] in ("one2many", "many2many") and i.get("relation") == "ir.attachment"
        ]

        lines.append("")
        lines.append("Binary fields on sign.template: %s" % (binary_fields or "none"))
        for name in binary_fields:
            try:
                lines.append("  - %s: %s" % (name, "HAS DATA" if self[name] else "empty"))
            except Exception as e:
                lines.append("  - %s: error reading (%s)" % (name, e))

        lines.append("Many2one fields to ir.attachment: %s" % (m2o_attach_fields or "none"))
        for name in m2o_attach_fields:
            try:
                lines.append("  - %s -> %s" % (name, self[name]))
            except Exception as e:
                lines.append("  - %s: error reading (%s)" % (name, e))

        lines.append("One2many/Many2many fields to ir.attachment: %s" % (x2m_attach_fields or "none"))
        for name in x2m_attach_fields:
            try:
                lines.append("  - %s -> %s records" % (name, len(self[name])))
            except Exception as e:
                lines.append("  - %s: error reading (%s)" % (name, e))

        doc_fields = [
            n for n, i in fields_info.items()
            if i.get("relation") == "sign.document"
        ]
        lines.append("")
        lines.append("Fields on sign.template relating to sign.document: %s" % (doc_fields or "none"))
        for name in doc_fields:
            try:
                value = self[name]
                lines.append("  - %s -> %s" % (name, value))
            except Exception as e:
                lines.append("  - %s: error reading (%s)" % (name, e))

        via_doc_attachment = self._get_pdf_via_sign_document()
        lines.append("PDF found via sign.document chain: %s" % (
            "id=%s (%s)" % (via_doc_attachment.id, via_doc_attachment.name)
            if via_doc_attachment else "no"
        ))

        # Broader net: any attachment anywhere with a similar filename,
        # in case the PDF is linked to a different model entirely.
        if self.name:
            by_name = self.env["ir.attachment"].search([
                ("name", "like", self.name[:20]),
            ], limit=10)
            lines.append("")
            lines.append("ir.attachment records with a similar name (any model): %s" % len(by_name))
            for a in by_name:
                lines.append("  - id=%s name=%r res_model=%r res_id=%s"
                             % (a.id, a.name, a.res_model, a.res_id))

        return "\n".join(lines)
