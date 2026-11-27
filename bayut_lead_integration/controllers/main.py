# -*- coding: utf-8 -*-
import hmac
import json
import logging
import xml.etree.ElementTree as ET

from odoo import fields, http
from odoo.http import request, Response

from ..models.bayut_connector import PUSH_PORTALS
from ..models.bayut_publish import _image_token

_logger = logging.getLogger(__name__)

PUBLIC_IMAGE_FIELDS = {"bayut.listing": "image_1920", "bayut.listing.image": "image"}


class BayutImageController(http.Controller):
    """Listing photos for Bayut: Bayut downloads images by URL, without an Odoo login.
    Each URL carries a per-photo token derived from the database secret."""

    @http.route("/bayut/image/<string:model>/<int:res_id>/<string:token>.jpg",
                type="http", auth="public", methods=["GET"], save_session=False)
    def bayut_listing_image(self, model, res_id, token, **kwargs):
        field = PUBLIC_IMAGE_FIELDS.get(model)
        if not field or not hmac.compare_digest(token, _image_token(request.env, model, res_id)):
            return request.not_found()
        record = request.env[model].sudo().browse(res_id).exists()
        if not record or not record[field]:
            return request.not_found()
        stream = request.env["ir.binary"]._get_image_stream_from(record, field)
        return stream.get_response(max_age=86400)


class BayutIntegrationController(http.Controller):
    """Provides:
    1. Live XML Listing Feed (`/bayut/feed/listings.xml`) for Bayut / Dubizzle Profolio.
    2. Live JSON Listing Feed (`/bayut/feed/listings.json`) for Bayut / Dubizzle Profolio.
    3. Incoming Webhook Endpoint (`/bayut/webhook/leads`) if Bayut pushes leads via webhook.
    """

    def _validate_token(self, req_token=None):
        """Validate optional Bearer header or ?token= query parameter against configured key."""
        params = request.env["ir.config_parameter"].sudo()
        configured_listing_key = (
            params.get_param("bayut_lead_integration.bayut_listing_api_key")
            or params.get_param("bayut_lead_integration.bayut_api_key")
            or ""
        ).strip()
        if not configured_listing_key:
            return True

        auth_header = request.httprequest.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            header_token = auth_header.replace("Bearer ", "", 1).strip()
            if header_token == configured_listing_key:
                return True

        if req_token and req_token.strip() == configured_listing_key:
            return True

        # Allow feed read access if no token was passed in query/header (standard Profolio XML poller)
        if not req_token and not auth_header:
            return True

        return False

    @http.route(
        ["/bayut/feed/listings.xml", "/bayut/listings.xml"],
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def bayut_listings_xml_feed(self, token=None, **kwargs):
        """Return published Bayut listings in standard Bayut/Dubizzle Profolio XML format."""
        if not self._validate_token(token):
            return Response("Unauthorized", status=401, content_type="text/plain")

        listings = (
            request.env["bayut.listing"]
            .sudo()
            .search([("state", "=", "published"), ("active", "=", True)], order="write_date desc, id desc")
        )

        root = ET.Element("Properties")
        now_str = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        root.set("last_update", now_str)
        root.set("count", str(len(listings)))

        for listing in listings:
            payload = listing._to_bayut_dict()
            prop_el = ET.SubElement(root, "Property")

            def _add_tag(parent, tag_name, val):
                el = ET.SubElement(parent, tag_name)
                el.text = "" if val is None or val is False else str(val)
                return el

            _add_tag(prop_el, "Property_Ref_No", payload.get("reference_number"))
            _add_tag(prop_el, "Permit_Number", payload.get("permit_number"))
            _add_tag(prop_el, "Property_purpose", payload.get("Purpose"))
            _add_tag(prop_el, "Property_Type", payload.get("property_type"))
            _add_tag(prop_el, "Property_Status", "live")
            _add_tag(prop_el, "City", payload.get("city"))
            _add_tag(prop_el, "Locality", payload.get("community"))
            _add_tag(prop_el, "Sub_Locality", payload.get("sub_community"))
            _add_tag(prop_el, "Tower_Name", payload.get("building_name"))
            _add_tag(prop_el, "Property_Title", payload.get("title_en"))
            _add_tag(prop_el, "Property_Title_AR", payload.get("title_ar"))
            _add_tag(prop_el, "Property_Description", payload.get("description_en"))
            _add_tag(prop_el, "Property_Description_AR", payload.get("description_ar"))
            _add_tag(prop_el, "Property_Size", payload.get("size_sqft"))
            _add_tag(prop_el, "Property_Size_Unit", "SQFT")
            _add_tag(prop_el, "Bedrooms", payload.get("bedrooms"))
            _add_tag(prop_el, "Bathrooms", payload.get("bathrooms"))
            _add_tag(prop_el, "Price", payload.get("price"))
            _add_tag(prop_el, "Rent_Frequency", payload.get("rent_frequency"))
            _add_tag(prop_el, "Furnished", payload.get("furnished"))
            _add_tag(prop_el, "Off_Plan", "Yes" if payload.get("completion_status") == "off_plan" else "No")
            _add_tag(prop_el, "Listing_Agent", payload.get("agent_name"))
            _add_tag(prop_el, "Listing_Agent_Email", payload.get("agent_email"))
            _add_tag(prop_el, "Listing_Agent_Phone", payload.get("agent_phone"))
            _add_tag(prop_el, "Last_Updated", payload.get("updated_at"))

            portals_el = ET.SubElement(prop_el, "Portals")
            for portal in payload.get("portals", ["bayut"]):
                _add_tag(portals_el, "Portal", portal)

            images_el = ET.SubElement(prop_el, "Images")
            for img_url in payload.get("images", []):
                _add_tag(images_el, "Image", img_url)

        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        return Response(xml_bytes, status=200, content_type="application/xml; charset=utf-8")

    @http.route(
        ["/bayut/feed/listings.json", "/bayut/listings.json"],
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def bayut_listings_json_feed(self, token=None, **kwargs):
        """Return published Bayut listings in JSON format."""
        if not self._validate_token(token):
            return Response(
                json.dumps({"error": "Unauthorized"}),
                status=401,
                content_type="application/json",
            )

        listings = (
            request.env["bayut.listing"]
            .sudo()
            .search([("state", "=", "published"), ("active", "=", True)], order="write_date desc, id desc")
        )
        data = {
            "status": "success",
            "count": len(listings),
            "updated_at": fields.Datetime.now().isoformat(),
            "listings": [l._to_bayut_dict() for l in listings],
        }
        return Response(
            json.dumps(data, indent=2),
            status=200,
            content_type="application/json; charset=utf-8",
        )

    @staticmethod
    def _json_response(data, status=200):
        return Response(json.dumps(data), status=status, content_type="application/json")

    def _handle_push_lead(self, portal):
        """Common handler for the Bayut / dubizzle Push API (call & WhatsApp leads).

        Authenticity: header X-Bayut-Signature / X-dubizzle-Signature = md5(secret_key + raw body).
        """
        header_name = PUSH_PORTALS[portal][0]
        raw_body = request.httprequest.get_data(cache=True) or b""
        signature = request.httprequest.headers.get(header_name, "")
        Connector = request.env["bayut.connector"].sudo()

        accepted, note = Connector._verify_push_signature(portal, raw_body, signature)
        if not accepted:
            _logger.warning("Rejected %s push lead: %s", portal, note)
            Connector.env["bayut.sync.log"].create({
                "connector_id": Connector._get_connector().id,
                "sync_type": "leads",
                "status": "error",
                "message": f"WEBHOOK {portal.upper()} rejected: {note}",
            })
            return self._json_response({"status": "error", "message": "Invalid signature"}, 401)

        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return self._json_response({"status": "error", "message": "Invalid JSON body"}, 400)

        try:
            result = Connector._process_incoming_leads_payload(
                payload, source="webhook", portal=portal, note=note
            )
            return self._json_response(result, 200)
        except Exception as exc:
            _logger.exception("Error processing %s push lead", portal)
            return self._json_response({"status": "error", "message": str(exc)}, 500)

    @http.route(["/bayut/webhook/leads"], type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def bayut_leads_webhook(self, **kwargs):
        """Bayut Push API endpoint (call leads & WhatsApp leads)."""
        return self._handle_push_lead("bayut")

    @http.route(["/dubizzle/webhook/leads"], type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def dubizzle_leads_webhook(self, **kwargs):
        """dubizzle Push API endpoint (WhatsApp leads)."""
        return self._handle_push_lead("dubizzle")
