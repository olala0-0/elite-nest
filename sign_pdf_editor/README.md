# Sign PDF Editor (Odoo 19)

Adds an **"Edit PDF"** button on Sign Templates to add text, images,
watermarks, and manage pages (rotate/delete/reorder/merge/split) directly
on the underlying PDF — before you place Sign fields or send it out.

## What this does / doesn't do

- ✅ Overlays new text, images, and watermarks onto the PDF (the same
  technique used by iLovePDF's "Edit PDF" tool and most online editors).
- ✅ Rotate, delete, reorder pages; merge in another PDF; split a page
  range into a brand-new template.
- ❌ Does **not** rewrite/reflow text that already exists in the PDF —
  PDFs don't store text as editable paragraphs the way Word does. True
  in-place text editing needs a commercial SDK (e.g. Nutrient/PSPDFKit,
  Apryse). This module covers the overlay-based workflow instead, which
  is what "PDF editors" generally mean in practice.

## Requirements

- Odoo 19, Sign app installed.
- Python package **PyMuPDF** (imported as `fitz`) on the server.

## Install on Odoo.sh

1. Add this folder (`sign_pdf_editor/`) into your repo, e.g. under
   `custom_addons/sign_pdf_editor/`.
2. Add a line to your repo's `requirements.txt` (at the root, alongside
   `odoo.conf`):
   ```
   PyMuPDF
   ```
   Odoo.sh installs this automatically on the next build.
3. Commit & push to your staging branch. Odoo.sh will rebuild.
4. In Odoo: Apps → remove the "Apps" filter, search **"Sign PDF Editor"**,
   click Install.

## Before going to production

The view file `views/sign_template_views.xml` uses a generic, safe xpath
(`//sheet` / inside) to place the button, since I don't have access to
verify the exact native `sign.template` form view XML for your specific
Odoo 19 build. **Test on staging first.** If the button doesn't appear
where you'd like, open:

`Settings → Technical → Views` (enable developer mode first) → search
`sign.template` → note the button/field names near where you want "Edit
PDF" to sit → adjust the `xpath expr` in `sign_template_views.xml`
accordingly.

## Known limitation to flag to your team

Deleting, reordering, or merging pages changes page numbers. Existing
Sign fields (the drag-and-drop signature/text boxes) are tied to a page
number + position, and are **not** automatically remapped. The wizard
shows a warning for these operations — always re-check field placement
afterward before sending a document for signature.
