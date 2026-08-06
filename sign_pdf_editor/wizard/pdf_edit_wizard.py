import base64
import io
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

FONT_MAP = {
    "helvetica": "helv",
    "times": "tiro",
    "courier": "cour",
}

# Best-fit mapping from a PDF's embedded/base font name to one of the three
# fonts we can actually draw with (PyMuPDF's Base14 set). This is a name
# heuristic, not real font matching - it won't reproduce the exact glyphs
# of a custom/embedded font, just picks the visually closest of our three
# options (serif / sans / monospace).
FONT_NAME_HINTS = (
    ("courier", "courier"), ("consol", "courier"), ("mono", "courier"),
    ("times", "times"), ("georgia", "times"), ("garamond", "times"),
    ("serif", "times"), ("cambria", "times"), ("minion", "times"),
)

# Plain strings, not _(): this dict is built at module import time, before
# any translation context exists, so wrapping these in _() here would do
# nothing useful anyway.
OPERATION_HELP = {
    "add_text": "Click the page below where you want the text to start, "
                 "then type it in and press Apply.",
    "add_image": "Click the page below where you want the top-left corner "
                 "of the image, then upload it and press Apply.",
    "watermark": "Applies a diagonal watermark across every page - "
                 "no position needed.",
    "rotate": "Rotates the pages you list by the chosen angle.",
    "delete": "Permanently removes the pages you list from this PDF.",
    "reorder": "Rearranges all pages into the order you specify.",
    "merge": "Inserts another PDF's pages into this one, after the page "
             "number you choose.",
    "split": "Copies a page range out into a brand-new template - the "
             "current template is left untouched.",
}


class SignPdfEditWizard(models.TransientModel):
    _name = "sign.pdf.edit.wizard"
    _description = "Edit Sign Template PDF"

    template_id = fields.Many2one("sign.template", required=True, ondelete="cascade")
    page_count = fields.Integer(readonly=True)
    debug_info = fields.Text(readonly=True, string="Diagnostic Info")
    show_diagnostics = fields.Boolean(default=False)

    operation = fields.Selection([
        ("add_text", "Add Text"),
        ("add_image", "Add Image / Stamp"),
        ("watermark", "Add Watermark"),
        ("rotate", "Rotate Pages"),
        ("delete", "Delete Pages"),
        ("reorder", "Reorder Pages"),
        ("merge", "Merge Another PDF"),
        ("split", "Split Pages Into New Template"),
    ], required=True, default="add_text")
    operation_help = fields.Char(compute="_compute_operation_help")

    @api.depends("operation")
    def _compute_operation_help(self):
        for wiz in self:
            wiz.operation_help = OPERATION_HELP.get(wiz.operation, "")

    # --- Add Text ---
    text_value = fields.Text(string="Text")
    text_page = fields.Integer(string="Page Number", default=1, help="1 = first page")
    text_pos_x = fields.Float(string="X Position (%)", default=10.0,
                               help="Horizontal position as % of page width from the left")
    text_pos_y = fields.Float(string="Y Position (%)", default=10.0,
                               help="Vertical position as % of page height from the top")
    text_font = fields.Selection([
        ("helvetica", "Helvetica (sans-serif)"),
        ("times", "Times (serif)"),
        ("courier", "Courier (monospace)"),
    ], default="helvetica")
    text_size = fields.Integer(string="Font Size", default=11)
    text_color = fields.Char(string="Color (hex)", default="#000000")
    detected_font_name = fields.Char(readonly=True, string="Detected Font On Page",
                                      help="Best-fit match, not the exact embedded font - "
                                           "PyMuPDF can only draw with Helvetica/Times/Courier.")

    # --- Add Image ---
    image_data = fields.Binary(string="Image")
    image_filename = fields.Char()
    image_page = fields.Integer(string="Page Number", default=1)
    image_pos_x = fields.Float(string="X Position (%)", default=10.0)
    image_pos_y = fields.Float(string="Y Position (%)", default=10.0)
    image_width = fields.Float(string="Width (%)", default=20.0,
                                help="Width as % of page width")

    # --- Watermark ---
    watermark_text = fields.Char(string="Watermark Text", default="DRAFT")
    watermark_opacity = fields.Float(string="Opacity (0-1)", default=0.15)
    watermark_size = fields.Integer(string="Font Size", default=60)

    # --- Rotate ---
    rotate_pages = fields.Char(string="Pages", default="all",
                                help="'all' or comma-separated list e.g. 1,3,5")
    rotate_angle = fields.Selection([
        ("90", "90°"), ("180", "180°"), ("270", "270°"),
    ], default="90")

    # --- Delete ---
    delete_pages_str = fields.Char(string="Pages to Delete",
                                    help="Comma-separated list e.g. 2,4")

    # --- Reorder ---
    reorder_str = fields.Char(string="New Page Order",
                               help="Comma-separated full list of page numbers in new order, e.g. 3,1,2")

    # --- Merge ---
    merge_pdf_data = fields.Binary(string="PDF to Merge")
    merge_pdf_filename = fields.Char()
    merge_insert_at = fields.Integer(string="Insert After Page", default=0,
                                      help="0 = insert at the very beginning")

    # --- Split ---
    split_range = fields.Char(string="Page Range", default="1-1",
                               help="e.g. 1-3")
    split_new_name = fields.Char(string="New Template Name")

    @api.onchange("template_id")
    def _onchange_template_id(self):
        for wiz in self:
            if not wiz.template_id:
                wiz.page_count = 0
                wiz.debug_info = ""
                continue
            wiz.page_count = wiz.template_id._get_page_count()
            wiz.debug_info = wiz.template_id._build_debug_info()
            wiz._detect_font()

    @api.onchange("text_page")
    def _onchange_text_page(self):
        for wiz in self:
            wiz._detect_font()

    def _detect_font(self):
        """Best-effort: look at what font the target page already uses and
        pre-select the closest of our three built-in fonts, so new text at
        least leans the same direction (serif/sans/mono) as the surrounding
        document instead of always defaulting to Helvetica."""
        self.ensure_one()
        self.detected_font_name = ""
        if not self.template_id:
            return
        try:
            import fitz
        except ImportError:
            return
        datas = self.template_id._get_pdf_datas()
        if not datas:
            return
        page_index = (self.text_page or 1) - 1
        try:
            doc = fitz.open(stream=base64.b64decode(datas), filetype="pdf")
            if page_index < 0 or page_index >= doc.page_count:
                doc.close()
                return
            page_fonts = doc[page_index].get_fonts(full=True)
            doc.close()
        except Exception:
            return
        if not page_fonts:
            return
        basefont = (page_fonts[0][3] or "").strip()
        if not basefont:
            return
        self.detected_font_name = basefont
        lower_name = basefont.lower()
        matched = "helvetica"
        for hint, choice in FONT_NAME_HINTS:
            if hint in lower_name:
                matched = choice
                break
        self.text_font = matched

    def _get_doc(self):
        try:
            import fitz
        except ImportError:
            raise UserError(_(
                "The PyMuPDF library ('fitz') is not installed on this server. "
                "Ask your administrator to add 'PyMuPDF' to requirements.txt."
            ))
        datas = self.template_id._get_pdf_datas()
        if not datas:
            raise UserError(_("This template has no PDF attached."))
        pdf_bytes = base64.b64decode(datas)
        return fitz, fitz.open(stream=pdf_bytes, filetype="pdf")

    def _save_doc(self, doc):
        out = io.BytesIO()
        doc.save(out)
        doc.close()
        out.seek(0)
        new_data = base64.b64encode(out.read())
        self.template_id._set_pdf_datas(new_data)

    def _parse_page_list(self, s, max_page):
        if not s:
            return []
        if s.strip().lower() == "all":
            return list(range(1, max_page + 1))
        pages = []
        for part in s.split(","):
            part = part.strip()
            if part:
                try:
                    pages.append(int(part))
                except ValueError:
                    raise UserError(_("Invalid page number: %s") % part)
        return pages

    def action_diagnose(self):
        """Refresh the diagnostic info and reveal it inline - not needed for
        normal use, only when something looks wrong and you want to see
        exactly where this PDF is being read from/written to."""
        self.ensure_one()
        if not self.template_id:
            raise UserError(_("Please select a template first."))
        self.debug_info = self.template_id._build_debug_info()
        self.show_diagnostics = True

    def action_hide_diagnostics(self):
        self.ensure_one()
        self.show_diagnostics = False

    def action_apply(self):
        self.ensure_one()
        method_name = "_apply_%s" % self.operation
        method = getattr(self, method_name, None)
        if not method:
            raise UserError(_("Unknown operation."))
        result_message = method()
        if self.template_id:
            self.page_count = self.template_id._get_page_count()
        reopen_action = {
            "type": "ir.actions.act_window",
            "name": _("Edit PDF"),
            "res_model": "sign.pdf.edit.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Applied"),
                "message": result_message or _("Change applied - preview updated below."),
                "type": "success",
                "next": reopen_action,
            },
        }

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def _apply_add_text(self):
        fitz, doc = self._get_doc()
        if not self.text_value:
            doc.close()
            raise UserError(_("Please enter text to add."))
        page_index = self.text_page - 1
        if page_index < 0 or page_index >= doc.page_count:
            doc.close()
            raise UserError(_("Invalid page number."))
        page = doc[page_index]
        rect = page.rect
        x = rect.width * (self.text_pos_x / 100.0)
        # insert_text's point is the text BASELINE, not the top-left corner -
        # without this offset, text renders shifted upward by about a
        # font-size from wherever you clicked, which is the "text doesn't
        # land where I click" bug. 0.8x is a standard approximation of a
        # font's ascent as a fraction of its em size.
        y = rect.height * (self.text_pos_y / 100.0) + (self.text_size * 0.8)
        color_hex = (self.text_color or "#000000").lstrip("#")
        color = tuple(int(color_hex[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        page.insert_text(
            (x, y),
            self.text_value,
            fontsize=self.text_size,
            fontname=FONT_MAP.get(self.text_font, "helv"),
            color=color,
        )
        self._save_doc(doc)

    def _apply_add_image(self):
        fitz, doc = self._get_doc()
        if not self.image_data:
            doc.close()
            raise UserError(_("Please upload an image."))
        page_index = self.image_page - 1
        if page_index < 0 or page_index >= doc.page_count:
            doc.close()
            raise UserError(_("Invalid page number."))
        page = doc[page_index]
        rect = page.rect
        img_bytes = base64.b64decode(self.image_data)
        x0 = rect.width * (self.image_pos_x / 100.0)
        y0 = rect.height * (self.image_pos_y / 100.0)
        w = rect.width * (self.image_width / 100.0)
        # keep aspect ratio using pixmap
        pix = fitz.Pixmap(img_bytes)
        aspect = pix.height / pix.width if pix.width else 1
        h = w * aspect
        image_rect = fitz.Rect(x0, y0, x0 + w, y0 + h)
        page.insert_image(image_rect, stream=img_bytes)
        self._save_doc(doc)

    def _apply_watermark(self):
        fitz, doc = self._get_doc()
        text = self.watermark_text or "DRAFT"
        for page in doc:
            rect = page.rect
            page.insert_text(
                (rect.width * 0.2, rect.height * 0.5),
                text,
                fontsize=self.watermark_size,
                fontname="helv",
                color=(0.6, 0.6, 0.6),
                rotate=45,
                fill_opacity=self.watermark_opacity,
            )
        self._save_doc(doc)

    def _apply_rotate(self):
        fitz, doc = self._get_doc()
        pages = self._parse_page_list(self.rotate_pages, doc.page_count)
        if not pages:
            doc.close()
            raise UserError(_("Specify which pages to rotate."))
        angle = int(self.rotate_angle)
        for p in pages:
            idx = p - 1
            if 0 <= idx < doc.page_count:
                page = doc[idx]
                page.set_rotation((page.rotation + angle) % 360)
        self._save_doc(doc)

    def _apply_delete(self):
        fitz, doc = self._get_doc()
        pages = self._parse_page_list(self.delete_pages_str, doc.page_count)
        if not pages:
            doc.close()
            raise UserError(_("Specify which pages to delete."))
        idxs = sorted({p - 1 for p in pages if 0 <= p - 1 < doc.page_count}, reverse=True)
        if len(idxs) >= doc.page_count:
            doc.close()
            raise UserError(_("Cannot delete all pages."))
        for idx in idxs:
            doc.delete_page(idx)
        self._save_doc(doc)
        self._warn_field_positions()

    def _apply_reorder(self):
        fitz, doc = self._get_doc()
        order = self._parse_page_list(self.reorder_str, doc.page_count)
        if sorted(order) != list(range(1, doc.page_count + 1)):
            doc.close()
            raise UserError(_(
                "New order must contain every page number exactly once (1 to %s)."
            ) % doc.page_count)
        idx_order = [p - 1 for p in order]
        doc.select(idx_order)
        self._save_doc(doc)
        self._warn_field_positions()

    def _apply_merge(self):
        fitz, doc = self._get_doc()
        if not self.merge_pdf_data:
            doc.close()
            raise UserError(_("Please upload a PDF to merge."))
        other_bytes = base64.b64decode(self.merge_pdf_data)
        other_doc = fitz.open(stream=other_bytes, filetype="pdf")
        insert_at = self.merge_insert_at or 0
        doc.insert_pdf(other_doc, start_at=insert_at)
        other_doc.close()
        self._save_doc(doc)
        self._warn_field_positions()

    def _apply_split(self):
        fitz, doc = self._get_doc()
        try:
            start_s, end_s = self.split_range.split("-")
            start, end = int(start_s), int(end_s)
        except Exception:
            doc.close()
            raise UserError(_("Page range must look like '1-3'."))
        if start < 1 or end > doc.page_count or start > end:
            doc.close()
            raise UserError(_("Invalid page range."))
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
        out = io.BytesIO()
        new_doc.save(out)
        new_doc.close()
        doc.close()
        out.seek(0)
        new_data = base64.b64encode(out.read())

        new_name = self.split_new_name or "%s (split)" % self.template_id.name
        new_template = self.env["sign.template"].create({"name": new_name})
        self.env["ir.attachment"].create({
            "name": new_name + ".pdf",
            "datas": new_data,
            "mimetype": "application/pdf",
            "res_model": "sign.template",
            "res_id": new_template.id,
        })
        return _("Created new template '%s' - the current template was left unchanged.") % new_name

    def _warn_field_positions(self):
        """Page count/order changed - existing Sign fields may now sit on the
        wrong page. We can't safely auto-remap them, so we just log it;
        the form view also shows a permanent warning banner for this reason.
        """
        _logger.info(
            "Sign PDF Editor: page structure of template %s changed. "
            "Existing sign.item field positions were not remapped.",
            self.template_id.id,
        )
