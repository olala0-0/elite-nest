import base64
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

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


class SignPdfEditWizard(models.TransientModel):
    _name = "sign.pdf.edit.wizard"
    _description = "Add Text to a Sign Template PDF"

    template_id = fields.Many2one("sign.template", required=True, ondelete="cascade")
    page_count = fields.Integer(readonly=True)
    debug_info = fields.Text(readonly=True, string="Diagnostic Info")
    show_diagnostics = fields.Boolean(default=False)

    text_overlay_ids = fields.One2many(related="template_id.text_overlay_ids", readonly=False)

    # --- New text to add ---
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
        # Read the pristine original, not the already-rendered PDF -
        # otherwise after the first text add, this just keeps re-detecting
        # our own inserted font instead of the document's real one.
        datas = self.template_id.pdf_original_data or self.template_id._get_pdf_datas()
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
        """Add the staged text (if any) as a new row, then redraw the PDF
        from the original plus every current row - including any edits or
        deletions made directly in the list above. One button covers both
        "add new text" and "fix/remove existing text"."""
        self.ensure_one()
        if not self.template_id:
            raise UserError(_("Please select a template first."))
        if self.text_value:
            self.env["sign.pdf.text.overlay"].create({
                "template_id": self.template_id.id,
                "page": self.text_page,
                "pos_x": self.text_pos_x,
                "pos_y": self.text_pos_y,
                "text_value": self.text_value,
                "font": self.text_font,
                "size": self.text_size,
                "color": self.text_color,
            })
            self.text_value = False
        self.template_id._render_text_overlays()
        self.page_count = self.template_id._get_page_count()
        try:
            self.env.user.notify_success(message=_("PDF updated."))
        except Exception:
            _logger.info("PDF updated for template %s", self.template_id.id)
        return {
            "type": "ir.actions.act_window",
            "name": _("Edit PDF"),
            "res_model": "sign.pdf.edit.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
