from odoo import models, fields

FONT_MAP = {
    "helvetica": "helv",
    "times": "tiro",
    "courier": "cour",
}


class SignPdfTextOverlay(models.Model):
    _name = "sign.pdf.text.overlay"
    _description = "Text Added to a Sign Template's PDF"
    _order = "sequence, id"

    template_id = fields.Many2one("sign.template", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    page = fields.Integer(string="Page", default=1, help="1 = first page")
    pos_x = fields.Float(string="X (%)", default=10.0,
                          help="Horizontal position as % of page width from the left")
    pos_y = fields.Float(string="Y (%)", default=10.0,
                          help="Vertical position as % of page height from the top")
    text_value = fields.Text(string="Text", required=True)
    font = fields.Selection([
        ("helvetica", "Helvetica"),
        ("times", "Times"),
        ("courier", "Courier"),
    ], default="helvetica", required=True)
    size = fields.Integer(string="Size", default=11)
    color = fields.Char(string="Color", default="#000000")
