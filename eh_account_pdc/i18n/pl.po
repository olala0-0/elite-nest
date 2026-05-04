# Translation of Odoo Server.
# This file contains the translation of the following modules:
# 	* eh_account_pdc
#
msgid ""
msgstr ""
"Project-Id-Version: ERP Heritage Accounting Suite 19.0\n"
"Report-Msgid-Bugs-To: info@erpheritage.com.au\n"
"POT-Creation-Date: 2026-05-03 12:00+0000\n"
"PO-Revision-Date: 2026-05-03 12:00+0000\n"
"Last-Translator: ERP Heritage <info@erpheritage.com.au>\n"
"Language-Team: pl_PL\n"
"Language: pl_PL\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "(no reason)"
msgstr "(no reason)"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "<strong>Cheques:</strong>"
msgstr "<strong>Cheques:</strong>"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "<strong>Company:</strong>"
msgstr "<strong>Company:</strong>"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "<strong>Generated:</strong>"
msgstr "<strong>Generated:</strong>"
#. module: eh_account_pdc
#: model:ir.model.constraint,message:eh_account_pdc.constraint_eh_cheque_uniq_book_serial
msgid "A cheque serial cannot be reused within the same book."
msgstr "A cheque serial cannot be reused within the same book."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_needaction
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_needaction
msgid "Action Needed"
msgstr "Action Needed"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_form
msgid "Activate"
msgstr "Activate"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__active
msgid "Active"
msgstr "Active"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__activity_ids
msgid "Activities"
msgstr "Activities"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__activity_exception_decoration
msgid "Activity Exception Decoration"
msgstr "Activity Exception Decoration"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__activity_state
msgid "Activity State"
msgstr "Activity State"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__activity_type_icon
msgid "Activity Type Icon"
msgstr "Activity Type Icon"
#. module: eh_account_pdc
#: model:ir.ui.menu,name:eh_account_pdc.menu_eh_cheque_all
msgid "All Cheques"
msgstr "All Cheques"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__amount
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "Amount"
msgstr "Amount"
#. module: eh_account_pdc
#: model:eh.cheque.bounce.reason,name:eh_account_pdc.bounce_reason_amount_mismatch
msgid "Amount in words and figures differs"
msgstr "Amount in words and figures differs"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_attachment_count
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_attachment_count
msgid "Attachment Count"
msgstr "Attachment Count"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__journal_id
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__journal_id
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "Bank Journal"
msgstr "Bank Journal"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__bounce_charges
msgid "Bank charges levied for the bounce, captured on customer side."
msgstr "Bank charges levied for the bounce, captured on customer side."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Bank journal %s has no Default Account configured."
msgstr "Bank journal %s has no Default Account configured."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid ""
"Bank journal %s has no Suspense Account configured. Set it on the journal "
"before processing PDC accounting."
msgstr "Bank journal %s has no Suspense Account configured. Set it on the journal before processing PDC accounting."
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Bounce"
msgstr "Bounce"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Bounce / Replacement"
msgstr "Bounce / Replacement"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__bounce_charges
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__bounce_charges
msgid "Bounce Charges"
msgstr "Bounce Charges"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_bounce_wizard_form
msgid "Bounce Cheque"
msgstr "Bounce Cheque"
#. module: eh_account_pdc
#: model:ir.model,name:eh_account_pdc.model_eh_cheque_bounce_wizard
msgid "Bounce Cheque Wizard"
msgstr "Bounce Cheque Wizard"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__bounce_move_id
msgid "Bounce Move"
msgstr "Bounce Move"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__bounce_notes
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Bounce Notes"
msgstr "Bounce Notes"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__bounce_reason_id
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_bounce_reason_form
msgid "Bounce Reason"
msgstr "Bounce Reason"
#. module: eh_account_pdc
#: model:ir.actions.act_window,name:eh_account_pdc.action_eh_cheque_bounce_reason
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_bounce_reason_tree
msgid "Bounce Reasons"
msgstr "Bounce Reasons"
#. module: eh_account_pdc
#: model:ir.model.constraint,message:eh_account_pdc.constraint_eh_cheque_bounce_reason_uniq_code
msgid "Bounce reason code must be unique."
msgstr "Bounce reason code must be unique."
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque__state__bounced
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Bounced"
msgstr "Bounced"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__bounced_at
msgid "Bounced At"
msgstr "Bounced At"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__bounced_by_id
msgid "Bounced By"
msgstr "Bounced By"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_bounce_wizard_form
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_replace_wizard_form
msgid "Cancel"
msgstr "Cancel"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Cancel this cheque?"
msgstr "Cancel this cheque?"
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque__state__cancelled
msgid "Cancelled"
msgstr "Cancelled"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__cancelled_at
msgid "Cancelled At"
msgstr "Cancelled At"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__cancelled_by_id
msgid "Cancelled By"
msgstr "Cancelled By"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__cheque_ids
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__cheque_id
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__cheque_id
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Cheque"
msgstr "Cheque"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "Cheque #"
msgstr "Cheque #"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid ""
"Cheque %(name)s cannot be presented before its value date %(value_date)s. "
"Today is %(today)s."
msgstr "Cheque %(name)s cannot be presented before its value date %(value_date)s. Today is %(today)s."
#. module: eh_account_pdc
#: model:ir.model,name:eh_account_pdc.model_eh_cheque_book
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__book_id
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_form
msgid "Cheque Book"
msgstr "Cheque Book"
#. module: eh_account_pdc
#: model:ir.actions.act_window,name:eh_account_pdc.action_eh_cheque_book
#: model:ir.ui.menu,name:eh_account_pdc.menu_eh_cheque_book
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_tree
msgid "Cheque Books"
msgstr "Cheque Books"
#. module: eh_account_pdc
#: model:ir.model,name:eh_account_pdc.model_eh_cheque_bounce_reason
msgid "Cheque Bounce Reason"
msgstr "Cheque Bounce Reason"
#. module: eh_account_pdc
#: model:ir.ui.menu,name:eh_account_pdc.menu_eh_cheque_bounce_reason
msgid "Cheque Bounce Reasons"
msgstr "Cheque Bounce Reasons"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__cheque_count
msgid "Cheque Count"
msgstr "Cheque Count"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__cheque_number
msgid "Cheque Number"
msgstr "Cheque Number"
#. module: eh_account_pdc
#: model:ir.actions.report,name:eh_account_pdc.action_report_cheque_register
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "Cheque Register"
msgstr "Cheque Register"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque_book.py:0
msgid "Cheque book %s has no serials remaining."
msgstr "Cheque book %s has no serials remaining."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
#: code:addons/eh_account_pdc/models/cheque_book.py:0
msgid "Cheque book %s is not active."
msgstr "Cheque book %s is not active."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque_book.py:0
msgid "Cheque book %s is not in draft state."
msgstr "Cheque book %s is not in draft state."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Cheque bounced: %s"
msgstr "Cheque bounced: %s"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid ""
"Cheque serial %(serial)s does not match the next available serial %(next)s "
"on book %(book)s. Refresh and try again, or close gaps in the book first."
msgstr "Cheque serial %(serial)s does not match the next available serial %(next)s on book %(book)s. Refresh and try again, or close gaps in the book first."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Cheque serial %(serial)s is outside book range %(start)s-%(end)s."
msgstr "Cheque serial %(serial)s is outside book range %(start)s-%(end)s."
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__cheque_number
msgid "Cheque serial number as printed on the cheque."
msgstr "Cheque serial number as printed on the cheque."
#. module: eh_account_pdc
#: model:ir.actions.act_window,name:eh_account_pdc.action_eh_cheque
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_tree
msgid "Cheques"
msgstr "Cheques"
#. module: eh_account_pdc
#: model:ir.ui.menu,name:eh_account_pdc.menu_eh_pdc_root
msgid "Cheques (PDC)"
msgstr "Cheques (PDC)"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_book__remaining_count
msgid "Cheques still available in the book based on next_number."
msgstr "Cheques still available in the book based on next_number."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__clear_move_id
msgid "Clear Move"
msgstr "Clear Move"
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque__state__cleared
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Cleared"
msgstr "Cleared"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__cleared_at
msgid "Cleared At"
msgstr "Cleared At"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__cleared_by_id
msgid "Cleared By"
msgstr "Cleared By"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Cleared or replaced cheques cannot be cancelled."
msgstr "Cleared or replaced cheques cannot be cancelled."
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_form
msgid "Close"
msgstr "Close"
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque_book__state__closed
msgid "Closed"
msgstr "Closed"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_form
msgid "Closing the book stops new cheques from drawing serials. Continue?"
msgstr "Closing the book stops new cheques from drawing serials. Continue?"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__code
msgid "Code"
msgstr "Code"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__company_id
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__company_id
msgid "Company"
msgstr "Company"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__partner_id
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "Counterparty"
msgstr "Counterparty"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_replace_wizard_form
msgid "Create Replacement"
msgstr "Create Replacement"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__create_uid
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__create_uid
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__create_uid
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__create_uid
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__create_uid
msgid "Created by"
msgstr "Created by"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__create_date
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__create_date
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__create_date
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__create_date
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__create_date
msgid "Created on"
msgstr "Created on"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__currency_id
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__currency_id
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__currency_id
msgid "Currency"
msgstr "Currency"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__issuer_account
msgid "Customer bank account masked or last 4 digits."
msgstr "Customer bank account masked or last 4 digits."
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__value_date
msgid "Date on which the cheque becomes presentable."
msgstr "Date on which the cheque becomes presentable."
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__issue_date
msgid "Date the cheque was written or received."
msgstr "Date the cheque was written or received."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__description
msgid "Description"
msgstr "Description"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__direction
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Direction"
msgstr "Direction"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__display_name
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__display_name
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__display_name
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__display_name
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__display_name
msgid "Display Name"
msgstr "Display Name"
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque__state__draft
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque_book__state__draft
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_search
msgid "Draft"
msgstr "Draft"
#. module: eh_account_pdc
#: model:eh.cheque.bounce.reason,name:eh_account_pdc.bounce_reason_account_closed
msgid "Drawer account closed"
msgstr "Drawer account closed"
#. module: eh_account_pdc
#: model:eh.cheque.bounce.reason,description:eh_account_pdc.bounce_reason_insufficient_funds
msgid "Drawer account did not hold sufficient balance at presentation."
msgstr "Drawer account did not hold sufficient balance at presentation."
#. module: eh_account_pdc
#: model:ir.actions.server,name:eh_account_pdc.ir_cron_auto_present_cheques_ir_actions_server
msgid "EH Account PDC: auto present cheques on value date"
msgstr "EH Account PDC: auto present cheques on value date"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_form
msgid "ENBD Operating Account 0001-1000"
msgstr "ENBD Operating Account 0001-1000"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__end_number
msgid "End Number"
msgstr "End Number"
#. module: eh_account_pdc
#: model:ir.model.constraint,message:eh_account_pdc.constraint_eh_cheque_book_check_range
msgid "End number must be greater than or equal to start number."
msgstr "End number must be greater than or equal to start number."
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque_book__state__exhausted
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_search
msgid "Exhausted"
msgstr "Exhausted"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_follower_ids
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_follower_ids
msgid "Followers"
msgstr "Followers"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_partner_ids
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_partner_ids
msgid "Followers (Partners)"
msgstr "Followers (Partners)"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__activity_type_icon
msgid "Font awesome icon e.g. fa-tasks"
msgstr "Font awesome icon e.g. fa-tasks"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__issuer_bank_name
msgid ""
"For incoming cheques: name of the bank the customer cheque is drawn on."
msgstr "For incoming cheques: name of the bank the customer cheque is drawn on."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__has_message
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__has_message
msgid "Has Message"
msgstr "Has Message"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__id
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__id
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__id
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__id
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__id
msgid "ID"
msgstr "ID"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__activity_exception_icon
msgid "Icon"
msgstr "Icon"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__activity_exception_icon
msgid "Icon to indicate an exception activity."
msgstr "Icon to indicate an exception activity."
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__message_needaction
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_book__message_needaction
msgid "If checked, new messages require your attention."
msgstr "If checked, new messages require your attention."
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__message_has_error
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__message_has_sms_error
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_book__message_has_error
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_book__message_has_sms_error
msgid "If checked, some messages have a delivery error."
msgstr "If checked, some messages have a delivery error."
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__replaced_by_id
msgid "If this cheque was replaced after a bounce, the new cheque."
msgstr "If this cheque was replaced after a bounce, the new cheque."
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_bounce_reason__is_recoverable
msgid ""
"If true, the cheque can typically be re-banked or replaced. If false (e.g. "
"account closed), expect direct write-off."
msgstr "If true, the cheque can typically be re-banked or replaced. If false (e.g. account closed), expect direct write-off."
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque_book__state__in_use
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_search
msgid "In Use"
msgstr "In Use"
#. module: eh_account_pdc
#: model:eh.cheque.bounce.reason,name:eh_account_pdc.bounce_reason_insufficient_funds
msgid "Insufficient funds"
msgstr "Insufficient funds"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_book__name
msgid ""
"Internal label for this cheque book. Often the bank name and serial range."
msgstr "Internal label for this cheque book. Often the bank name and serial range."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_is_follower
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_is_follower
msgid "Is Follower"
msgstr "Is Follower"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__is_overdue
msgid "Is Overdue"
msgstr "Is Overdue"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__is_recoverable
msgid "Is Recoverable"
msgstr "Is Recoverable"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__issue_date
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "Issue Date"
msgstr "Issue Date"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Issued"
msgstr "Issued"
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque__direction__outgoing
msgid "Issued (Payable)"
msgstr "Issued (Payable)"
#. module: eh_account_pdc
#: model:ir.actions.act_window,name:eh_account_pdc.action_eh_cheque_outgoing
#: model:ir.ui.menu,name:eh_account_pdc.menu_eh_cheque_outgoing
msgid "Issued Cheques"
msgstr "Issued Cheques"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Issued cheques require a cheque book."
msgstr "Issued cheques require a cheque book."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__issuer_account
msgid "Issuer Account"
msgstr "Issuer Account"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__issuer_bank_name
msgid "Issuer Bank"
msgstr "Issuer Bank"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_search
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Journal"
msgstr "Journal"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque_book.py:0
msgid ""
"Journal %(journal)s already has an active cheque book (%(book)s). Close it "
"before activating a new one."
msgstr "Journal %(journal)s already has an active cheque book (%(book)s). Close it before activating a new one."
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__clear_move_id
msgid "Journal entry posted on clearance (suspense → bank)."
msgstr "Journal entry posted on clearance (suspense → bank)."
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__present_move_id
msgid "Journal entry posted on present (deposit / issue)."
msgstr "Journal entry posted on present (deposit / issue)."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__write_uid
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__write_uid
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__write_uid
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__write_uid
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__write_uid
msgid "Last Updated by"
msgstr "Last Updated by"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__write_date
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__write_date
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__write_date
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__write_date
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__write_date
msgid "Last Updated on"
msgstr "Last Updated on"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Linked Documents"
msgstr "Linked Documents"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__invoice_id
msgid "Linked Invoice"
msgstr "Linked Invoice"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__payment_id
msgid "Linked Payment"
msgstr "Linked Payment"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Mark Cleared"
msgstr "Mark Cleared"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_has_error
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_has_error
msgid "Message Delivery error"
msgstr "Message Delivery error"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_ids
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_ids
msgid "Messages"
msgstr "Messages"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__my_activity_date_deadline
msgid "My Activity Deadline"
msgstr "My Activity Deadline"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__name
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__name
msgid "Name"
msgstr "Name"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__new_amount
msgid "New Amount"
msgstr "New Amount"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__new_book_id
msgid "New Book"
msgstr "New Book"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__new_cheque_number
msgid "New Cheque Number"
msgstr "New Cheque Number"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__new_value_date
msgid "New Value Date"
msgstr "New Value Date"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__activity_date_deadline
msgid "Next Activity Deadline"
msgstr "Next Activity Deadline"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__activity_summary
msgid "Next Activity Summary"
msgstr "Next Activity Summary"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__activity_type_id
msgid "Next Activity Type"
msgstr "Next Activity Type"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__next_number
msgid "Next Number"
msgstr "Next Number"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_book__next_number
msgid ""
"Next available cheque serial. Updated automatically when a cheque is "
"registered against this book."
msgstr "Next available cheque serial. Updated automatically when a cheque is registered against this book."
#. module: eh_account_pdc
#: model:ir.model.constraint,message:eh_account_pdc.constraint_eh_cheque_book_check_next_in_range
msgid "Next number must be within the book range or just past the end."
msgstr "Next number must be within the book range or just past the end."
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "No cheques selected."
msgstr "No cheques selected."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__notes
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__notes
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__notes
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_replace_wizard__notes
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_form
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Notes"
msgstr "Notes"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_needaction_counter
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_needaction_counter
msgid "Number of Actions"
msgstr "Number of Actions"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_has_error_counter
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_has_error_counter
msgid "Number of errors"
msgstr "Number of errors"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__message_needaction_counter
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_book__message_needaction_counter
msgid "Number of messages requiring action"
msgstr "Number of messages requiring action"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__message_has_error_counter
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_book__message_has_error_counter
msgid "Number of messages with delivery error"
msgstr "Number of messages with delivery error"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
#: code:addons/eh_account_pdc/wizards/replace_cheque_wizard.py:0
msgid "Only bounced cheques can be replaced."
msgstr "Only bounced cheques can be replaced."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Only draft cheques can be registered."
msgstr "Only draft cheques can be registered."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
#: code:addons/eh_account_pdc/wizards/bounce_cheque_wizard.py:0
msgid "Only presented cheques can be bounced."
msgstr "Only presented cheques can be bounced."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Only presented cheques can be marked as cleared."
msgstr "Only presented cheques can be marked as cleared."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Only registered cheques can be presented to the bank."
msgstr "Only registered cheques can be presented to the bank."
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Open"
msgstr "Open"
#. module: eh_account_pdc
#: model:eh.cheque.bounce.reason,name:eh_account_pdc.bounce_reason_other
msgid "Other"
msgstr "Other"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Outgoing cheque serial must be numeric within a cheque book."
msgstr "Outgoing cheque serial must be numeric within a cheque book."
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Overdue"
msgstr "Overdue"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "PDC %s: %s"
msgstr "PDC %s: %s"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Partner"
msgstr "Partner"
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Partner %s has no %s account configured for company %s."
msgstr "Partner %s has no %s account configured for company %s."
#. module: eh_account_pdc
#: model:ir.model,name:eh_account_pdc.model_eh_cheque
msgid "Post Dated Cheque"
msgstr "Post Dated Cheque"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__present_move_id
msgid "Present Move"
msgstr "Present Move"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Present at Bank"
msgstr "Present at Bank"
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque__state__presented
msgid "Presented"
msgstr "Presented"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__presented_at
msgid "Presented At"
msgstr "Presented At"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__presented_by_id
msgid "Presented By"
msgstr "Presented By"
#. module: eh_account_pdc
#: model:eh.cheque.bounce.reason,name:eh_account_pdc.bounce_reason_post_dated
msgid "Presented before value date"
msgstr "Presented before value date"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_wizard__reason_id
msgid "Reason"
msgstr "Reason"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Received"
msgstr "Received"
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque__direction__incoming
msgid "Received (Receivable)"
msgstr "Received (Receivable)"
#. module: eh_account_pdc
#: model:ir.actions.act_window,name:eh_account_pdc.action_eh_cheque_incoming
#: model:ir.ui.menu,name:eh_account_pdc.menu_eh_cheque_incoming
msgid "Received Cheques"
msgstr "Received Cheques"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_bounce_wizard_form
msgid "Record Bounce"
msgstr "Record Bounce"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__name
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "Reference"
msgstr "Reference"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Register"
msgstr "Register"
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque__state__registered
msgid "Registered"
msgstr "Registered"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__remaining_count
msgid "Remaining Count"
msgstr "Remaining Count"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_form
msgid "Replace"
msgstr "Replace"
#. module: eh_account_pdc
#: model:ir.model,name:eh_account_pdc.model_eh_cheque_replace_wizard
msgid "Replace Bounced Cheque"
msgstr "Replace Bounced Cheque"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_replace_wizard_form
msgid "Replace Cheque"
msgstr "Replace Cheque"
#. module: eh_account_pdc
#: model:ir.model.fields.selection,name:eh_account_pdc.selection__eh_cheque__state__replaced
msgid "Replaced"
msgstr "Replaced"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__replaced_by_id
msgid "Replaced By"
msgstr "Replaced By"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__replaces_id
msgid "Replaces"
msgstr "Replaces"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__book_id
msgid "Required for issued cheques. Drives serial allocation."
msgstr "Required for issued cheques. Drives serial allocation."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__activity_user_id
msgid "Responsible User"
msgstr "Responsible User"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__bounce_move_id
msgid "Reversal of the present entry, posted on bounce."
msgstr "Reversal of the present entry, posted on bounce."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__message_has_sms_error
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__message_has_sms_error
msgid "SMS Delivery error"
msgstr "SMS Delivery error"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_bounce_reason__sequence
msgid "Sequence"
msgstr "Sequence"
#. module: eh_account_pdc
#: model:eh.cheque.bounce.reason,name:eh_account_pdc.bounce_reason_signature
msgid "Signature mismatch or missing"
msgstr "Signature mismatch or missing"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__start_number
msgid "Start Number"
msgstr "Start Number"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__state
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__state
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_book_search
msgid "State"
msgstr "State"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Status"
msgstr "Status"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__activity_state
msgid ""
"Status based on activities\n"
"Overdue: Due date is already passed\n"
"Today: Activity date is today\n"
"Planned: Future activities."
msgstr "Status based on activities\\nOverdue: Due date is already passed\\nToday: Activity date is today\\nPlanned: Future activities."
#. module: eh_account_pdc
#: model:eh.cheque.bounce.reason,name:eh_account_pdc.bounce_reason_stop_payment
msgid "Stop payment instructed"
msgstr "Stop payment instructed"
#. module: eh_account_pdc
#: model:eh.cheque.bounce.reason,name:eh_account_pdc.bounce_reason_technical
msgid "Technical (mutilated, image quality)"
msgstr "Technical (mutilated, image quality)"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__replaces_id
msgid "The original cheque this record replaces."
msgstr "The original cheque this record replaces."
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_tree
msgid "Total"
msgstr "Total"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__activity_exception_decoration
msgid "Type of the exception activity on record."
msgstr "Type of the exception activity on record."
#. module: eh_account_pdc
#. odoo-python
#: code:addons/eh_account_pdc/models/cheque.py:0
msgid "Unsupported search operator on is_overdue."
msgstr "Unsupported search operator on is_overdue."
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__value_date
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.report_cheque_register
msgid "Value Date"
msgstr "Value Date"
#. module: eh_account_pdc
#: model_terms:ir.ui.view,arch_db:eh_account_pdc.view_eh_cheque_search
msgid "Value Month"
msgstr "Value Month"
#. module: eh_account_pdc
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque__website_message_ids
#: model:ir.model.fields,field_description:eh_account_pdc.field_eh_cheque_book__website_message_ids
msgid "Website Messages"
msgstr "Website Messages"
#. module: eh_account_pdc
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque__website_message_ids
#: model:ir.model.fields,help:eh_account_pdc.field_eh_cheque_book__website_message_ids
msgid "Website communication history"
msgstr "Website communication history"
