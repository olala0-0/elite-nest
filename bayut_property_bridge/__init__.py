# -*- coding: utf-8 -*-
import logging

from . import models

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Link existing listings to their property (from the legacy integer field) and
    re-sync the property-owned unit data.
    Pushes to Bayut are skipped here; the regular listing cron / XML feed picks them up."""
    Listing = env["bayut.listing"].sudo().with_context(active_test=False)
    Property = env["property.detail"].sudo()
    linked = 0
    for listing in Listing.search([("source_property_ref", "!=", 0), ("property_id", "=", False)]):
        prop = Property.browse(listing.source_property_ref).exists()
        if not prop or Listing.search_count([("property_id", "=", prop.id)]):
            continue
        listing.with_context(skip_bayut_auto_sync=True).write({"property_id": prop.id})
        linked += 1
    synced = Property.search([("bayut_listing_ids", "!=", False)])._bayut_sync_listings(push=False)
    _logger.info("bayut_property_bridge: linked %s listing(s), re-synced %s listing(s).", linked, synced)
