{
    "name": "Sign PDF Editor",
    "version": "19.0.1.0.0",
    "category": "Productivity/Sign",
    "summary": "Edit PDF content (text, images, watermark, pages) directly on Sign templates before sending for signature.",
    "description": """
Sign PDF Editor
================
Adds an "Edit PDF" action on Sign Templates (sign.template) that lets you:

- Add text overlays (choose font, size, color, position, page)
- Add image overlays / stamps / logos
- Add a watermark across all pages
- Rotate pages
- Delete pages
- Reorder pages
- Merge another PDF in
- Split out a range of pages into a new template

All operations act on the underlying PDF attachment of the template, so the
result looks like native, edited PDF content — not an Odoo Sign form field.

Note: this module overlays new content onto the PDF (the same approach used
by most online "PDF editors"). It does not reflow or rewrite existing text
that is already embedded in the PDF, since PDFs don't store text as editable
paragraphs. For that level of editing, a commercial PDF SDK is required.
""",
    "author": "Custom Development",
    "license": "LGPL-3",
    "depends": ["sign"],
    "external_dependencies": {
        "python": ["fitz"],  # PyMuPDF
    },
    "data": [
        "security/ir.model.access.csv",
        "wizard/pdf_edit_wizard_views.xml",
        "views/sign_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sign_pdf_editor/static/src/css/pdf_page_picker.css",
            "sign_pdf_editor/static/src/js/pdf_page_picker.js",
            "sign_pdf_editor/static/src/xml/pdf_page_picker.xml",
        ],
    },
    "installable": True,
    "application": False,
}
