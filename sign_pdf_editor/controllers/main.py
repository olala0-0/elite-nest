import base64

from odoo import http
from odoo.http import request


class SignPdfEditorController(http.Controller):
    """Serves the PDF being edited so the wizard's visual page picker
    (pdf.js, running in the browser) can render it. Delegates to
    sign.template._get_pdf_datas(), which already knows every storage
    pattern this PDF might live under (direct attachment, relation field,
    sign.document field) - the controller doesn't need to guess again.
    """

    @http.route("/sign_pdf_editor/preview/<int:wizard_id>", type="http", auth="user")
    def preview_pdf(self, wizard_id, **kwargs):
        wizard = request.env["sign.pdf.edit.wizard"].browse(wizard_id).exists()
        if not wizard or not wizard.template_id:
            return request.not_found()

        datas = wizard.template_id._get_pdf_datas()
        if not datas:
            return request.not_found()

        pdf_bytes = base64.b64decode(datas)
        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", str(len(pdf_bytes))),
            ("Content-Disposition", "inline"),
        ]
        return request.make_response(pdf_bytes, headers=headers)
