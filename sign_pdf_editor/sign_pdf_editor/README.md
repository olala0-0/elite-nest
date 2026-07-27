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

## Where to find it

Odoo's Sign template screen (the drag-and-drop field editor you see when
you open a template) is a custom frontend component, not a normal Odoo
form — so this module does **not** try to inject a button into that
screen. Instead it adds its own menu:

**Top menu bar → "PDF Editor" → "Edit PDF"**

Pick your template from the dropdown at the top of the wizard, choose an
operation, fill in the fields, and click Apply. The change is written to
the template's PDF attachment immediately — reopen the template's normal
editor screen afterward to confirm it, place/adjust Sign fields, etc.

If you'd rather this live nested inside the existing "Sign" app menu
instead of its own top-level entry, open Settings → Technical → Menu
Items (developer mode on) and note the exact menu you want it under —
send me that and I'll adjust the `parent` safely without guessing.

## Known limitation to flag to your team

Deleting, reordering, or merging pages changes page numbers. Existing
Sign fields (the drag-and-drop signature/text boxes) are tied to a page
number + position, and are **not** automatically remapped. The wizard
shows a warning for these operations — always re-check field placement
afterward before sending a document for signature.
