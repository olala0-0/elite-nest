# -*- coding: utf-8 -*-
"""1.0.1: replace the old placeholder / wrong Bayut endpoints stored in existing databases."""
import logging

_logger = logging.getLogger(__name__)

NEW_LEADS_URL = "https://api.bayut.com/v1/leads"
NEW_PROPERTIES_URL = "https://api.bayut.com/v1/properties"


def migrate(cr, version):
    cr.execute(
        "UPDATE ir_config_parameter SET value = %s "
        "WHERE key = 'bayut_lead_integration.bayut_api_url' AND value LIKE %s",
        (NEW_LEADS_URL, "%leads-api.bayut.com%"),
    )
    cr.execute(
        "UPDATE ir_config_parameter SET value = %s "
        "WHERE key = 'bayut_lead_integration.bayut_listing_api_url' AND value = %s",
        (NEW_PROPERTIES_URL, "https://api.bayut.com/v1/listings"),
    )
    cr.execute(
        "UPDATE bayut_connector SET api_url = %s WHERE api_url LIKE %s",
        (NEW_LEADS_URL, "%leads-api.bayut.com%"),
    )
    cr.execute(
        "UPDATE bayut_connector SET listing_api_url = %s WHERE listing_api_url = %s",
        (NEW_PROPERTIES_URL, "https://api.bayut.com/v1/listings"),
    )
    _logger.info("bayut_lead_integration 1.0.1: Bayut endpoint URLs updated.")
