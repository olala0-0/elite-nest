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

    def _get_sign_documents(self):
        """All sign.document records related to this template, via any
        Many2one/One2many/Many2many field pointing to sign.document."""
        self.ensure_one()
        if "sign.document" not in self.env:
            return self.env["sign.document"]
        fields_info = self.fields_get(attributes=["type", "relation"])
        docs = self.env["sign.document"]
        for name, info in fields_info.items():
            if info.get("relation") != "sign.document":
                continue
            if info.get("type") == "many2one":
                docs |= self[name]
            elif info.get("type") in ("one2many", "many2many"):
                docs |= self[name]
        return docs

    def _get_binary_field_candidates(self, record):
        """Binary field names on `record`'s model, best-guess-first."""
        fields_info = record.fields_get(attributes=["type"])
        names = [n for n, i in fields_info.items() if i["type"] == "binary"]
        names.sort(key=lambda n: (
            0 if any(k in n.lower() for k in ("attach", "pdf", "doc", "data")) else 1
        ))
        return names

    def _get_pdf_via_sign_document(self):
        """Pattern 3: sign.template links to a separate sign.document
        record (Many2one, One2many, or Many2many). Read the PDF directly
        off a Binary field on that record via the ORM (not by guessing
        which ir.attachment belongs to it) - this matters because a single
        sign.document can have several ir.attachment rows against it (one
        per attachment=True Binary field, tagged by res_field), so picking
        'whichever has the highest id' can silently read/write the wrong
        one. Returns (document_record, field_name) or (None, None)."""
        self.ensure_one()
        for doc in self._get_sign_documents():
            for field_name in self._get_binary_field_candidates(doc):
                if doc[field_name]:
                    return doc, field_name
        return None, None

    def _get_pdf_via_sign_document_attachment_guess(self):
        """Last-resort fallback: guess the sign.document's attachment by
        res_model/res_id alone, ignoring res_field. Kept only in case a
        sign.document's PDF isn't reachable through any of its own Binary
        fields for some reason - prefer _get_pdf_via_sign_document()."""
        self.ensure_one()
        doc_ids = self._get_sign_documents().ids
        if not doc_ids:
            return None
        return self.env["ir.attachment"].search([
            ("res_model", "=", "sign.document"),
            ("res_id", "in", doc_ids),
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
        doc, field_name = self._get_pdf_via_sign_document()
        if doc:
            return doc[field_name]
        via_doc_guess = self._get_pdf_via_sign_document_attachment_guess()
        if via_doc_guess and via_doc_guess.datas:
            return via_doc_guess.datas
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
        doc, field_name = self._get_pdf_via_sign_document()
        if doc:
            doc.write({field_name: new_data})
            return
        via_doc_guess = self._get_pdf_via_sign_document_attachment_guess()
        if via_doc_guess:
            via_doc_guess.write({"datas": new_data})
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

        docs = self._get_sign_documents()
        lines.append("")
        lines.append("sign.document record(s) found: %s" % (docs.ids or "none"))
        for doc in docs:
            binary_fields = self._get_binary_field_candidates(doc)
            lines.append("  - sign.document(%s): binary fields = %s" % (doc.id, binary_fields or "none"))
            for field_name in binary_fields:
                has_data = bool(doc[field_name])
                lines.append("      %s: %s" % (field_name, "HAS DATA" if has_data else "empty"))
            doc_attachments = self.env["ir.attachment"].search([
                ("res_model", "=", "sign.document"),
                ("res_id", "=", doc.id),
            ])
            lines.append("      ir.attachment rows against this document: %s" % len(doc_attachments))
            for a in doc_attachments:
                lines.append("        id=%s name=%r res_field=%r has_datas=%s"
                             % (a.id, a.name, a.res_field, bool(a.datas)))

        doc, field_name = self._get_pdf_via_sign_document()
        lines.append("")
        lines.append("PDF resolved via sign.document field: %s" % (
            "sign.document(%s).%s" % (doc.id, field_name) if doc else "no"
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
