{
    "name": "Sign PDF Editor",
    "version": "19.0.1.1.0",
    "category": "Productivity/Sign",
    "summary": "Add text overlays directly on Sign templates before sending for signature.",
    "description": """
Sign PDF Editor
================
Adds an "Edit PDF" action on Sign Templates (sign.template) that lets you add
text onto the PDF (choose font, size, color, position, page) before you place
Sign fields or send it out.

Each piece of added text is kept as an editable row linked to the template -
not burned permanently into the PDF on first save. The PDF is always
regenerated from a saved pristine original plus the current set of rows, so
fixing a typo or removing a row and clicking Apply again gives a clean
result, with no drift from repeated edits.

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
