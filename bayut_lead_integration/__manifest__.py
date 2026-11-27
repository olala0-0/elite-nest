# -*- coding: utf-8 -*-
{
    "name": "Bayut Lead & Listing Integration",
    "version": "1.0.5",
    "category": "Sales/CRM",
    "summary": "Bayut / dubizzle Profolio: real-time leads into Odoo CRM and live listing status from Bayut",
    "description": """
Bayut Lead & Listing Integration
================================
* **Leads**: real-time Push API webhooks (Bayut + dubizzle, calls + WhatsApp, signed with
  X-Bayut-Signature / X-dubizzle-Signature) and a backup pull from ``GET /v1/leads``.
  Leads are de-duplicated and assigned to the matching agent / default sales team.
* **Listings**: publish, update and unpublish on Bayut from Odoo (``/v1/properties`` +
  ``/products/attach``, Bayut portal only), with validation before sending, public photo links
  and live location search. Odoo mirrors the real status of every Profolio listing.
* **Honest logging**: Sync Logs show success only for real 2xx answers from Bayut.
* The Profolio API token is entered in Settings; it is never shipped with the module.
    """,
    "author": "Elite Nest",
    "license": "LGPL-3",
    "depends": [
        "crm",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/bayut_listing_views.xml",
        "views/bayut_sync_log_views.xml",
        "views/bayut_connector_views.xml",
        "views/crm_lead_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": [
        "static/description/icon.svg",
    ],
    "installable": True,
    "application": True,
    "auto_install": True,
}
