# Bayut Lead Integration (`bayut_lead_integration`)

Odoo CRM integration module that imports real estate inquiries, call logs, WhatsApp messages, and contact intent signals from the **Bayut Leads API** into `crm.lead`.

---

## 1. Module Structure

```text
bayut_lead_integration/
├── __init__.py
├── __manifest__.py
├── README.md
├── data/
│   └── ir_cron_data.xml
├── models/
│   ├── __init__.py
│   ├── bayut_connector.py
│   ├── bayut_sync_log.py
│   ├── crm_lead.py
│   └── res_config_settings.py
├── security/
│   └── ir.model.access.csv
└── views/
    ├── bayut_connector_views.xml
    ├── bayut_sync_log_views.xml
    ├── crm_lead_views.xml
    └── res_config_settings_views.xml
```

---

## 2. Installation & Setup Steps

1. **Install the Module**:
   - Navigate to **Apps** in Odoo, click **Update Apps List**, search for **Bayut Lead Integration** (`bayut_lead_integration`), and click **Activate**.
2. **Configure Bayut API Credentials**:
   - Go to **Settings > General Settings > CRM** and scroll to the **Bayut Leads Integration** section:
     - **Bayut API URL**: Defaults to `https://leads-api.bayut.com/`. Replace this with the exact production endpoint provided by Bayut Support once received.
     - **Bayut API Key**: Enter your Bearer API key provided by Bayut (masked with password widget).
     - **Default Sales Team**: Select the CRM team (`crm.team`) for new Bayut leads.
     - **Default Salesperson**: Select the user (`res.users`) assigned to new Bayut leads.
     - **Sync Interval (Minutes)**: Defaults to `10` minutes. Saving Settings automatically updates the **Bayut: Sync Leads** scheduled cron job (`ir.cron`).
3. **Test Connection & Manual Sync**:
   - Click **Test Connection** in Settings to verify that your API URL and Bearer key respond with HTTP 200.
   - Click **Sync Now** to immediately run a lead synchronization and view the result in **Recent Bayut Sync Logs**.

---

## 3. Where to Update the Real API Endpoint & Payload Mapping Once Bayut Support Replies

### A. Updating the Endpoint URL & Key (No Code Changes Required)
Go to **Settings > General Settings > CRM > Bayut Leads Integration**:
- Paste the official endpoint URL into **Bayut API URL**.
- Paste the production token into **Bayut API Key** and click **Save**.

### B. Adapting the JSON Response Format (`_parse_lead`)
All JSON payload field extraction is isolated in a single method in [`models/bayut_connector.py`](models/bayut_connector.py):

```python
@api.model
def _parse_lead(self, raw_lead):
    """Parse a single lead dictionary from the Bayut API response into a
    normalized dictionary used by Odoo CRM.
    TODO: Update the field key mappings below once Bayut Support provides
    the official Leads API response documentation.
    """
```

If Bayut's official API uses different key names (for example, `leadId` instead of `id` or `listing_ref` instead of `property_ref`), you only need to update `_parse_lead()` in `models/bayut_connector.py` (and the top-level list key `payload.get("leads", [])` in `cron_sync_leads()` if the outer wrapper key differs).

---

## 4. De-duplication & Intent Signals

- **Primary De-duplication**: Every imported lead stores `bayut_lead_id` (indexed + unique constraint). If a `crm.lead` with the same `bayut_lead_id` already exists, it is skipped.
- **Customer & Lead Matching**: Matches existing `res.partner` records by email or normalized phone number (`last 9 digits`) and links `partner_id`. If an active open lead already exists for the same customer and the same `bayut_property_ref`, the new activity is logged in the existing lead's chatter instead of creating a duplicate.
- **Intent Signals (`phone_view` & `sms_click`)**: Automatically created with **Low Priority (`0`)** and annotated with a note indicating that the event is an intent signal rather than a full inquiry lead.
