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

## Fixed in this version

Odoo 19's `sign.template` model does **not** expose a direct `attachment_id`
field — the PDF is stored as a separate `ir.attachment` record linked via
`res_model`/`res_id`. All code now looks it up that way instead of
assuming a field name. If you hit another `Unknown field` install error
anywhere, send me the exact error text (it names the missing field) and
I'll correct it the same way — I can't inspect your live schema directly,
so these fixes are reactive to what your server reports.

**Test "Merge" and "Split" on staging specifically** — they create/link
new `ir.attachment`/`sign.template` records, which is the area most
likely to depend on internal fields I can't fully verify from here.

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

## Visual page picker (Add Text / Add Image)

The wizard now renders the actual PDF page inline (using Odoo's own bundled
pdf.js) for the **Add Text** and **Add Image / Stamp** operations. Click
directly on the page and the X/Y position fields fill in automatically -
you can still edit those number fields by hand afterward to fine-tune.

**Confirmed working on this instance**: pdf.js loads fine from
`/web/static/lib/pdfjs/build/pdf.js`, and the PDF is correctly located via
the `sign.document` field fix above.

One thing that still relies on you testing:

- **Widget registration API**: uses the `view_widgets` registry and
  `standardWidgetProps` from `@web/views/widgets/standard_widget_props`,
  the standard pattern for non-field form widgets in recent Odoo web
  client versions. If the wizard fails to open at all after upgrading
  (rather than just failing to render the PDF), check the browser
  console for a JS import error and send me the exact message.

The other operations (Rotate/Delete/Reorder/Merge/Split, and Watermark)
don't need a click position, so they keep their existing plain fields.

## Known limitation to flag to your team

Deleting, reordering, or merging pages changes page numbers. Existing
Sign fields (the drag-and-drop signature/text boxes) are tied to a page
number + position, and are **not** automatically remapped. The wizard
shows a warning for these operations — always re-check field placement
afterward before sending a document for signature.
