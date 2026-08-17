# Sign PDF Editor (Odoo 19)

Adds an **"Edit PDF"** button on Sign Templates to add text onto the
underlying PDF — before you place Sign fields or send it out.

## What this does / doesn't do

- ✅ Overlays new text onto the PDF (the same technique used by iLovePDF's
  "Edit PDF" tool and most online editors).
- ✅ Every piece of added text stays editable: fix a typo or remove a line
  and re-apply — see "Editing / undoing added text" below.
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
   click Install (or Upgrade if already installed).

## Where to find it

Odoo's Sign template screen (the drag-and-drop field editor you see when
you open a template) is a custom frontend component, not a normal Odoo
form — so this module does **not** try to inject a button into that
screen. Instead it adds its own menu:

**Top menu bar → "PDF Editor" → "Edit PDF"**

Pick your template from the dropdown, click on the page preview where you
want text to start, type it in, and click Apply.

## Editing / undoing added text

Every piece of text you add is kept as its own row (page, position, text,
font, size, color) linked to the template — not burned permanently into
the PDF the moment you click Apply. Each time you click Apply, the PDF is
rebuilt from scratch from a saved pristine copy of the original file plus
every row currently in the list, so:

- **Fix a typo**: edit the text directly in the "Text Already On This PDF"
  list and click Apply.
- **Undo an addition**: click the trash icon on that row and click Apply.
  Since the PDF is always rebuilt from the original, the removed text is
  gone from the result — it doesn't leave a trace.

**Caveat**: text added through an earlier version of this module (before
this row-based system existed) was burned directly into the PDF with no
backup taken. That existing text is not retroactively split out into an
editable row — it's just part of the base document now. Everything added
going forward through this version is fully editable/removable as above.

## Text placement accuracy

Click position maps to the exact spot on the page, and text is anchored
to its baseline using the actual font's ascender metric (not a guessed
offset), so the first line lands exactly where you clicked rather than
starting either above or below it.

Font: PyMuPDF can only draw with three built-in fonts (Helvetica, Times,
Courier). The wizard auto-detects the page's existing font and pre-selects
the closest visual match (serif/sans/mono) — it won't reproduce the exact
embedded font, just lean the same direction.

## Known limitation to flag to your team

The visual page picker relies on Odoo's own bundled pdf.js
(`/web/static/lib/pdfjs/build/pdf.js`) to render the page preview in the
browser. If that ever fails to load (banner shown in the wizard), you can
still type the page number and X/Y percentages by hand.
