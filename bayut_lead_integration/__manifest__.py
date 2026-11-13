# -*- coding: utf-8 -*-
{
    "name": "Bayut Lead & Listing Integration",
    "version": "17.0.2.0.0",
    "category": "Sales/CRM",
    "summary": "Standalone Bayut Profolio App: Manage & Push Property Listings, XML/JSON Feeds, and Sync Bayut Leads into Odoo CRM",
    "description": """
Bayut Lead & Listing Integration (Standalone Odoo App)
======================================================
Complete standalone application for managing **Bayut & Dubizzle Profolio Property Listings**
and importing **Bayut Leads & Intent Signals** into Odoo CRM (`crm.lead`).

Key Features:
-------------
1. **Standalone Bayut Integration Application**:
   - Top-level menu (**Bayut Integration**) with **Listings**, **Bayut Leads**, **Connector Hub**, **Sync Logs**, and **Settings**.
2. **Bayut Listing Management (`bayut.listing`)**:
   - Create, edit, price, and publish listings directly from Odoo since Profolio locks manual editing when Listing API integration is active.
   - Pre-configured with the agency's Bayut Listing API Token (`96522341|rB11mebGgqYvMIIquvTlT9T23ESdNv3mmjSGbFq876729d9f`).
   - One-click **Publish to Bayut Profolio**, **Push Update to Bayut**, **Unpublish**, and automatic sync when a published listing is edited.
   - Live **XML Feed** (`/bayut/feed/listings.xml`) and **JSON Feed** (`/bayut/feed/listings.json`) endpoints for Bayut/Dubizzle Profolio.
   - Optional one-click import from `property.detail` if `eg_property_management` is installed.
3. **Bayut Leads Synchronization (`crm.lead`)**:
   - Scheduled cron job (`Bayut: Sync Leads`) and real-time webhook (`/bayut/webhook/leads`).
   - Isolated `_parse_lead()` and `_prepare_listing_payload()` methods on `bayut.connector`.
   - Automatic de-duplication by `bayut_lead_id`, smart customer/lead matching by email & phone, and low-priority (`0`) classification for `phone_view` and `sms_click` intent signals.
    """,
    "author": "Elite Nest",
    "license": "LGPL-3",
    "depends": [
        "crm",
    ],
    "data": [
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
