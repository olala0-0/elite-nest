import base64

from odoo import http
from odoo.http import request


class SignPdfEditorController(http.Controller):
    """Serves the PDF being edited so the wizard's visual page picker
    (pdf.js, running in the browser) can render it. Delegates to
    sign.template._get_pdf_datas(), which already knows every storage
    pattern this PDF might live under (direct attachment, relation field,
    sign.document field) - the controller doesn't need to guess again.

    Keyed by template_id rather than the wizard's own id: the wizard is a
    transient record and its client-side resId isn't reliably available
    to the widget at the moment it needs to build this URL, whereas the
    template_id is already read directly off the form for the "is this
    operation applicable" check, so reusing it here avoids that gap.
    """

    @http.route("/sign_pdf_editor/preview/<int:template_id>", type="http", auth="user")
    def preview_pdf(self, template_id, **kwargs):
        template = request.env["sign.template"].browse(template_id).exists()
        if not template:
            return request.not_found()

        datas = template._get_pdf_datas()
        if not datas:
            return request.not_found()

        pdf_bytes = base64.b64decode(datas)
        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", str(len(pdf_bytes))),
            ("Content-Disposition", "inline"),
        ]
        return request.make_response(pdf_bytes, headers=headers)
