# -*- coding: utf-8 -*-
{
    "name": "Bayut ↔ Property Management Bridge",
    "version": "1.0.0",
    "category": "Sales/CRM",
    "summary": "Links Bayut listings to Property Management units: the property is the master "
               "record for unit data, the Bayut listing is its marketing layer.",
    "description": """
Bayut ↔ Property Management Bridge
==================================
* Real link (Many2one) between ``bayut.listing`` and ``property.detail`` (one listing per unit).
* Unit data (purpose, type, beds, baths, parking, furnishing) is owned by the
  property and synced instantly to the listing (read-only there).
* Price and size are separate fields on each side: pre-filled once on the listing, then edited there.
* Marketing data (titles, descriptions, permit, agent, photos, location wording) stays on the listing.
* Status rules are manual: Occupied / Sold -> "Unpublish" alert + activity for the agent;
  Vacant again -> "Ready to re-list" alert + activity. Nothing is published or unpublished automatically.
* Bayut leads are linked to the property through the listing.
    """,
    "author": "Elite Nest",
    "license": "LGPL-3",
    "depends": [
        "bayut_lead_integration",
        "eg_property_management",
    ],
    "data": [
        "views/bayut_listing_views.xml",
        "views/property_detail_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": True,
}
