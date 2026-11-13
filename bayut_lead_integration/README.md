# Bayut Lead & Listing Integration (`bayut_lead_integration`)

Standalone Odoo application that manages **Bayut & Dubizzle Profolio Property Listings** (`bayut.listing`) and imports **Bayut Leads** (`crm.lead`) into Odoo CRM.

---

## 1. Why This Standalone App Is Needed

When the Bayut team activates **Listing API Integration** on an agency's **Profolio™** account, manual editing of property listings inside Profolio is locked and all listing creation, pricing, photo updates, DLD permits, and publishing must be done from the CRM.

This module works **100% standalone** (requiring only `crm`) and provides:
1. **Top-Level "Bayut Integration" App** in the Odoo App Switcher:
   - **Listings (`bayut.listing`)**: Create, edit, price, upload photos, set DLD/RERA Permit numbers, and click **Publish to Bayut Profolio** / **Push Update to Bayut** / **Unpublish from Bayut**.
   - **Bayut Leads (`crm.lead`)**: View and manage all incoming Bayut inquiries, call logs, WhatsApp leads, and intent signals (`phone_view`, `sms_click`).
   - **Connector Hub (`bayut.connector`)**: Pre-loaded with your Bayut Listing API Key (`96522341|rB11mebGgqYvMIIquvTlT9T23ESdNv3mmjSGbFq876729d9f`), live XML/JSON Feed URLs, Webhook URL, **Test Connection**, **Sync Listings to Bayut**, **Sync Leads Now**, and one-click **Import Units from Property Management**.
   - **Sync Logs (`bayut.sync.log`)**: Complete execution history for both Listing pushes and Lead syncs.
2. **Live Profolio XML & JSON Feed Endpoints**:
   - `GET /bayut/feed/listings.xml`
   - `GET /bayut/feed/listings.json`
   - `POST /bayut/webhook/leads`

---

## 2. Pre-Configured Token & Setup

- **Pre-loaded Listing & Leads API Key**:
  `96522341|rB11mebGgqYvMIIquvTlT9T23ESdNv3mmjSGbFq876729d9f`
- You can view or update the API URLs and keys at any time in:
  - **Bayut Integration > Connector Hub**, or
  - **Settings > CRM > Bayut Lead & Listing Integration**.

---

## 3. Adapting Payload Schemas (`models/bayut_connector.py`)

All payload mapping is isolated in two methods inside [`models/bayut_connector.py`](models/bayut_connector.py):
- `_parse_lead(self, raw_lead)` — parses incoming lead dictionaries from Bayut.
- `_prepare_listing_payload(self, listing, action="publish")` — formats outgoing property listing payloads for Bayut Profolio.
