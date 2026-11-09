# -*- coding: utf-8 -*-
{
    "name": "Bayut Lead Integration",
    "version": "17.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Import real estate leads and intent signals from the Bayut Leads API into Odoo CRM",
    "description": """
Bayut Lead Integration for Odoo CRM
===================================
Automatically synchronizes property inquiries, call logs, WhatsApp leads, and intent signals
(phone views, SMS clicks) from the Bayut Leads API into Odoo CRM (`crm.lead`).

Key Features:
-------------
- Configurable Bayut API URL, API Key (Bearer Token), Default Sales Team, Default Salesperson, and Sync Interval under **Settings > CRM**.
- **Test Connection** & **Sync Now** actions directly from CRM Settings.
- Scheduled Cron Job (`Bayut: Sync Leads`) running every N minutes.
- Isolated `_parse_lead()` method on `bayut.connector` for effortless adaptation once Bayut Support provides the final API payload schema.
- Automatic de-duplication by `bayut_lead_id` and smart customer/lead matching by email and phone.
- Automatic low-priority (`0`) classification and intent-signal note for `phone_view` and `sms_click` events.
- Full execution history via `bayut.sync.log` visible directly in Settings.
    """,
    "author": "Elite Nest",
    "license": "LGPL-3",
    "depends": [
        "crm",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/bayut_sync_log_views.xml",
        "views/bayut_connector_views.xml",
        "views/crm_lead_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": True,
}
