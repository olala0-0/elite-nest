# Bayut Lead & Listing Integration (`bayut_lead_integration`)

Connects Odoo with **Bayut / dubizzle Profolio**:

- **Leads → Odoo CRM**
  - Real time through the Push API webhooks:
    - `POST /bayut/webhook/leads` (header `X-Bayut-Signature`)
    - `POST /dubizzle/webhook/leads` (header `X-dubizzle-Signature`)
    - Signature = `md5(secret_key + raw_body)`; the secret is entered in Settings.
  - Backup pull from `GET https://api.bayut.com/v1/leads` (phone + WhatsApp, `is_lead=1`).
    First run looks back 60 days, then the last 3 days on every run. Duplicates are skipped.
- **Listings**
  - Odoo reads the real status of your listings from `GET https://api.bayut.com/v1/properties`
    (every 15 minutes, or **Refresh from Bayut** in the Connector Hub).
  - Publishing from Odoo is not connected yet: create, edit and publish listings in Profolio.

## Setup

1. **Settings → CRM → Bayut**: enter the Profolio API token (Bayut Leads API Key / Listing API Key)
   and the Push secret keys. Tokens are never stored in the module code.
2. Give the webhook URLs to Bayut support (support@bayut.com) and dubizzle (ps-reply@dubizzle.com).
3. **Connector Hub → Test Connection** must report "Connected to Bayut Profolio (HTTP 200)".

## Access

Only members of the **Bayut Integration** group (administrators by default) see the app.

## API reference

Base URL `https://api.bayut.com/v1`, header `Authorization: Bearer <token>`.
Rate limit is read from the `X-RateLimit-*` headers; HTTP 429 is retried after `retry_after`.
