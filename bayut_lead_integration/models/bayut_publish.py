# -*- coding: utf-8 -*-
"""Publish Odoo listings to Bayut through the Profolio API (Bayut portal only for now).

Flow per listing: validate -> POST /v1/properties (new) or PUT /v1/properties/{id} (all fields)
-> POST /v1/properties/{id}/products/attach {"portal": "bayut"} -> GET /v1/properties/{id}
to read the real state. Nothing is marked Published unless Bayut says the listing is live.
"""
import hashlib
import hmac
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .bayut_connector import ACTIVE_PORTAL, BAYUT_API_BASE

_logger = logging.getLogger(__name__)

# Odoo listing property_type -> Bayut category slug (GET /v1/categories)
CATEGORY_SLUGS = {
    "Apartment": "apartments",
    "Villa": "villas",
    "Townhouse": "townhouses",
    "Penthouse": "penthouse",
    "Hotel Apartment": "hotel-apartments",
    "Residential Building": "residential-building",
    "Residential Plot": "residential-plots",
    "Office": "offices",
    "Shop": "shops",
    "Warehouse": "warehouses",
    "Commercial Building": "commercial-buildings",
    "Commercial Plot": "commercial-plots",
}
VIDEO_HOSTS = (("youtube", "youtube"), ("youtu.be", "youtube"), ("vimeo", "vimeo"),
               ("dailymotion", "dailymotion"), ("matterport", "3d_view"))
TITLE_MAX = 100
DESCRIPTION_MAX = 8000


def _image_token(env, model, res_id):
    """Unguessable token so Bayut can download listing photos without an Odoo login."""
    secret = env["ir.config_parameter"].sudo().get_param("database.secret") or ""
    return hmac.new(secret.encode(), f"bayut-image:{model}:{res_id}".encode(), hashlib.sha256).hexdigest()[:32]


class BayutLocation(models.Model):
    """Bayut locations (GET /v1/locations), fetched live while the user types."""
    _name = "bayut.location"
    _description = "Bayut Location"
    _order = "name"

    name = fields.Char(string="Location", required=True, index=True)
    bayut_id = fields.Integer(string="Bayut Location ID", required=True, index=True)
    path = fields.Char(string="Full Path", help="UAE > Dubai > ... > building")

    @api.constrains("bayut_id")
    def _check_unique_bayut_id(self):
        for rec in self:
            if self.search_count([("bayut_id", "=", rec.bayut_id), ("id", "!=", rec.id)]):
                raise UserError(_("Bayut location %s already exists.", rec.bayut_id))

    @api.depends("name", "path")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.path or rec.name

    @api.model
    def _upsert_from_bayut(self, loc):
        """Create/update a location from a Bayut location object; returns the record."""
        if not isinstance(loc, dict) or not loc.get("id"):
            return self.browse()
        title = loc.get("title")
        name = (title.get("en") if isinstance(title, dict) else title) or str(loc["id"])
        crumbs = (loc.get("breadcrumb") or {}).get("en") or []
        vals = {"name": name, "bayut_id": int(loc["id"]), "path": " > ".join(crumbs) or name}
        rec = self.sudo().search([("bayut_id", "=", vals["bayut_id"])], limit=1)
        if rec:
            if rec.name != vals["name"] or rec.path != vals["path"]:
                rec.write(vals)
            return rec
        return self.sudo().create(vals)

    @api.model
    def _fetch_from_bayut(self, text):
        connector = self.env["bayut.connector"].sudo()
        cfg = connector._get_config_settings()
        token = cfg["listing_api_key"] or cfg["api_key"]
        if not token or len(text or "") < 3:
            return
        ok, status, body = connector._bayut_request(
            "GET", f"{BAYUT_API_BASE}/locations", token, params={"title": text, "per_page": 20}
        )
        if ok and isinstance(body, dict):
            for loc in body.get("data") or []:
                self._upsert_from_bayut(loc)

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        if name and len(name) >= 3:
            try:
                self._fetch_from_bayut(name)
            except Exception:
                _logger.exception("Bayut location lookup failed for %r", name)
        domain = list(domain or [])
        if name:
            domain = ["|", ("name", operator, name), ("path", operator, name)] + domain
            name = ""
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)


class BayutListingImage(models.Model):
    _inherit = "bayut.listing.image"

    remote_url = fields.Char(
        string="Bayut Image URL",
        help="Photo already hosted by Bayut (imported from Profolio). Sent back as-is on update.",
    )

    def _bayut_public_url(self):
        self.ensure_one()
        if self.remote_url:
            return self.remote_url
        if not self.image:
            return ""
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
        return f"{base}/bayut/image/bayut.listing.image/{self.id}/{_image_token(self.env, self._name, self.id)}.jpg"


class BayutListing(models.Model):
    _inherit = "bayut.listing"

    state = fields.Selection(
        selection_add=[("pending", "Pending on Bayut"), ("inactive", "Inactive on Bayut")],
        ondelete={"pending": "set default", "inactive": "set default"},
    )
    bayut_location = fields.Many2one(
        "bayut.location", string="Bayut Location",
        help="Building / community as Bayut knows it. Type at least 3 letters, e.g. 'La Perla'.",
    )
    ownership_status = fields.Selection(
        [("freehold", "Freehold"), ("leasehold", "Leasehold")], string="Ownership", default="freehold",
    )
    permit_status = fields.Char(string="Permit Status (Bayut)", readonly=True)
    verification_state = fields.Char(string="Bayut Verification", readonly=True)
    bayut_portal_status = fields.Char(string="Portal Status", readonly=True)
    bayut_extra_json = fields.Text(
        string="Bayut-only Details", readonly=True, copy=False,
        help="Amenities and rental terms kept on Bayut but not edited in Odoo. Sent back unchanged on "
             "every update, because Bayut replaces the whole listing on update.",
    )

    # ------------------------------------------------------------------
    # Payload
    # ------------------------------------------------------------------
    def _bayut_images_payload(self):
        self.ensure_one()
        images = []
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
        if self.image_1920:
            images.append({
                "title": (self.name or "")[:255],
                "path": f"{base}/bayut/image/bayut.listing/{self.id}/"
                        f"{_image_token(self.env, self._name, self.id)}.jpg",
                "is_main": True,
            })
        for img in self.image_ids:
            url = img._bayut_public_url()
            if url:
                images.append({"title": (img.name or None), "path": url, "is_main": not images})
        return images[:100]

    def _bayut_location_id(self):
        self.ensure_one()
        if self.bayut_location:
            return self.bayut_location.bayut_id
        try:
            return int(self.bayut_location_id or 0) or False
        except ValueError:
            return False

    def _bayut_user_fields(self, connector, token):
        """Bayut agent: the Bayut user with the agent's email, else the default Bayut user."""
        self.ensure_one()
        email = (self.agent_email or self.agent_user_id.email or self.agent_user_id.login or "").strip()
        if email and "@" in email:
            ok, status, body = connector._bayut_request(
                "GET", f"{BAYUT_API_BASE}/users", token, params={"email": email, "per_page": 5}
            )
            if ok:
                for user in body.get("data") or []:
                    if ((user.get("contact") or {}).get("email") or "").lower() == email.lower():
                        return {"user_id": int(user["id"])}
        default_id = self.env["ir.config_parameter"].sudo().get_param(
            "bayut_lead_integration.bayut_default_bayut_user_id")
        if default_id and str(default_id).isdigit():
            return {"user_id": int(default_id)}
        return {}

    def _bayut_check_ready(self):
        """List of missing / invalid items, in plain words. Empty = ready to send."""
        self.ensure_one()
        problems = []
        if not (self.name or "").strip():
            problems.append(_("Listing title"))
        elif len(self.name) > TITLE_MAX:
            problems.append(_("Listing title is %s characters; Bayut allows at most %s", len(self.name), TITLE_MAX))
        if not (self.description_en or "").strip():
            problems.append(_("English description"))
        if not self.price or self.price < 1:
            problems.append(_("Price"))
        if not self.size_sqft or self.size_sqft < 1:
            problems.append(_("Size (Sqft)"))
        if not self._bayut_location_id():
            problems.append(_("Bayut Location (building)"))
        if self.property_type not in CATEGORY_SLUGS:
            problems.append(_("Property type"))
        if not self._bayut_images_payload():
            problems.append(_("At least one photo"))
        permit = (self.permit_number or "").strip()
        if not permit:
            problems.append(_("DLD / RERA permit number"))
        else:
            # One DLD permit = one unit = one live listing on Bayut
            other = self.sudo().with_context(active_test=False).search([
                ("permit_number", "=", permit), ("id", "!=", self.id),
                ("state", "in", ("published", "pending")),
            ], limit=1)
            if other:
                problems.append(_(
                    "Permit %(permit)s is already used by listing %(ref)s, which is live or pending on Bayut. "
                    "Each permit can only be advertised once",
                    permit=permit, ref=other.reference_number))
        return problems

    def _bayut_property_payload(self, user_fields):
        """Full property body for POST and PUT (PUT must always carry every field)."""
        self.ensure_one()
        bedrooms = int(self.bedrooms or 0)
        payload = {
            "reference": self.reference_number,
            "title": {"en": self.name.strip()[:TITLE_MAX], "ar": (self.title_ar or None) and self.title_ar[:TITLE_MAX]},
            "description": {"en": self.description_en.strip()[:DESCRIPTION_MAX],
                            "ar": (self.description_ar or None) and self.description_ar[:DESCRIPTION_MAX]},
            "purpose": "sale" if self.purpose == "for-sale" else "rent",
            "category": CATEGORY_SLUGS[self.property_type],
            "location_id": self._bayut_location_id(),
            "construction_status": "under-construction" if self.completion_status == "off_plan" else "completed",
            "price": float(self.price),
            "area": float(self.size_sqft),
            "bedrooms": -1 if bedrooms == 0 else bedrooms,
            "bathrooms": int(self.bathrooms or 0),
            "permit_number": (self.permit_number or "").strip() or None,
            "ownership_status": self.ownership_status or "freehold",
            "images": self._bayut_images_payload(),
        }
        try:
            extra = json.loads(self.bayut_extra_json or "{}")
        except ValueError:
            extra = {}
        if self.furnished in ("furnished", "unfurnished"):
            payload["furnishing_status"] = self.furnished
        elif extra.get("furnishing_status") in ("furnished", "unfurnished"):
            payload["furnishing_status"] = extra["furnishing_status"]
        if payload["purpose"] == "rent":
            rental = {k: v for k, v in (extra.get("rental_details") or {}).items() if v is not None}
            rental["rent_frequency"] = self.rent_frequency or rental.get("rent_frequency") or "yearly"
            payload["rental_details"] = rental
        if extra.get("amenities"):
            payload["amenities"] = extra["amenities"][:100]
        videos = []
        for url in (self.video_url, self.virtual_tour_url):
            host = next((h for key, h in VIDEO_HOSTS if url and key in url), None)
            if host:
                videos.append({"title": None, "host": host, "link": url})
        if videos:
            payload["videos"] = videos
        payload.update(user_fields)
        return payload

    # ------------------------------------------------------------------
    # Bayut calls
    # ------------------------------------------------------------------
    def _bayut_log(self, status, message):
        connector = self.env["bayut.connector"].sudo()._get_connector()
        self.env["bayut.sync.log"].sudo().create({
            "connector_id": connector.id,
            "sync_datetime": fields.Datetime.now(),
            "sync_type": "listings",
            "status": status,
            "listings_synced": len(self),
            "message": message,
        })

    def _bayut_refresh_one(self, connector, token):
        """Read this listing from Bayut and store the real state."""
        self.ensure_one()
        ok, status, body = connector._bayut_request("GET", f"{BAYUT_API_BASE}/properties/{self.bayut_external_id}", token)
        if status == 404:
            self.with_context(skip_bayut_auto_sync=True).write({
                "state": "unpublished", "bayut_external_id": False, "bayut_portal_status": False,
                "last_bayut_sync": fields.Datetime.now(),
                "last_sync_message": _("No longer on Bayut."),
            })
            return
        if ok and isinstance(body, dict) and isinstance(body.get("data"), dict):
            self.with_context(skip_bayut_auto_sync=True).write(connector._bayut_status_vals(body["data"], self))
            connector._bayut_import_images(self, body["data"])

    def _bayut_send(self, publish):
        connector = self.env["bayut.connector"].sudo()
        cfg = connector._get_config_settings()
        token = cfg["listing_api_key"] or cfg["api_key"]
        if not token:
            raise UserError(_("Enter the Bayut Profolio API token in Settings first."))
        done, failed = [], []
        for listing in self:
            if listing.bayut_external_id:
                # Load Bayut's current amenities / photos / terms first: PUT replaces everything
                listing._bayut_refresh_one(connector, token)
            problems = listing._bayut_check_ready()
            if problems:
                raise UserError(_(
                    "%(ref)s can't be sent to Bayut yet. Please complete:\n- %(items)s",
                    ref=listing.reference_number, items="\n- ".join(problems),
                ))
            payload = listing._bayut_property_payload(listing._bayut_user_fields(connector, token))
            if not payload.get("user_id"):
                raise UserError(_(
                    "No Bayut agent found for %s. Set the Default Bayut Agent in Settings "
                    "(Test Connection fills it in when your agency has one Bayut user).", listing.reference_number))
            if listing.bayut_external_id:
                ok, status, body = connector._bayut_request(
                    "PUT", f"{BAYUT_API_BASE}/properties/{listing.bayut_external_id}", token, json_body=payload)
                step = _("update")
            else:
                ok, status, body = connector._bayut_request("POST", f"{BAYUT_API_BASE}/properties", token, json_body=payload)
                step = _("create")
                if ok and isinstance(body.get("data"), dict) and body["data"].get("id"):
                    listing.with_context(skip_bayut_auto_sync=True).write(
                        {"bayut_external_id": str(body["data"]["id"])})
            if not ok:
                reason = (_("Bayut is still processing this listing; try again in a minute.") if status == 409
                          else connector._bayut_error_text(status, body))
                failed.append(f"{listing.reference_number} ({step}): {reason}")
                listing.message_post(body=_("Bayut %(step)s failed: %(reason)s", step=step, reason=reason))
                continue
            live = (listing.bayut_portal_status or "").find(f"{ACTIVE_PORTAL}: active") >= 0
            if publish and not live:
                ok, status, body = connector._bayut_request(
                    "POST", f"{BAYUT_API_BASE}/properties/{listing.bayut_external_id}/products/attach",
                    token, json_body={"portal": ACTIVE_PORTAL})
                if not ok and status != 409:
                    reason = connector._bayut_error_text(status, body)
                    failed.append(f"{listing.reference_number} (publish): {reason}")
                    listing.message_post(body=_("Bayut publish failed: %s", reason))
            listing._bayut_refresh_one(connector, token)
            state_label = dict(listing._fields["state"].selection).get(listing.state)
            if publish and listing.state != "published":
                failed.append(_("%(ref)s was sent but is %(state)s: %(why)s",
                                ref=listing.reference_number, state=state_label,
                                why=listing.permit_status or _("Bayut has not made it live yet")))
            else:
                done.append(f"{listing.reference_number}: {state_label}")
            listing.message_post(body=_("Sent to Bayut (%(step)s). Bayut status: %(st)s",
                                        step=step, st=listing.bayut_portal_status or "-"))
        msg = _("Bayut: %(ok)d listing(s) sent, %(ko)d failed.", ok=len(done), ko=len(failed))
        if done:
            msg += "\n" + "\n".join(done)
        if failed:
            msg += "\n" + _("Errors:") + "\n" + "\n".join(failed)
        self._bayut_log("error" if failed else "success", msg)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Bayut"), "message": msg,
                       "type": "danger" if failed else "success", "sticky": bool(failed)},
        }

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_publish_to_bayut(self):
        return self._bayut_send(publish=True)

    def action_update_on_bayut(self):
        return self._bayut_send(publish=False)

    def action_unpublish_from_bayut(self):
        """Remove the listing from the Bayut portal (Bayut has no 'deactivate', only delete).
        The form button asks for confirmation first."""
        connector = self.env["bayut.connector"].sudo()
        cfg = connector._get_config_settings()
        token = cfg["listing_api_key"] or cfg["api_key"]
        if not token:
            raise UserError(_("Enter the Bayut Profolio API token in Settings first."))
        done, failed = [], []
        for listing in self.filtered("bayut_external_id"):
            ok, status, body = connector._bayut_request(
                "DELETE", f"{BAYUT_API_BASE}/properties/{listing.bayut_external_id}", token,
                json_body={"portals": [ACTIVE_PORTAL]})
            if not ok and status != 404:
                reason = connector._bayut_error_text(status, body)
                failed.append(f"{listing.reference_number}: {reason}")
                listing.message_post(body=_("Bayut unpublish failed: %s", reason))
                continue
            listing._bayut_refresh_one(connector, token)
            if listing.state == "published":
                listing.with_context(skip_bayut_auto_sync=True).write({"state": "unpublished"})
            done.append(listing.reference_number)
            listing.message_post(body=_("Removed from Bayut by %s.", self.env.user.name))
        msg = _("Removed from Bayut: %(ok)s. Failed: %(ko)s",
                ok=", ".join(done) or "-", ko="; ".join(failed) or "-")
        self._bayut_log("error" if failed else "success", msg)
        return {"type": "ir.actions.client", "tag": "display_notification",
                "params": {"title": _("Bayut"), "message": msg,
                           "type": "danger" if failed else "success", "sticky": bool(failed)}}

    def action_refresh_from_bayut(self):
        connector = self.env["bayut.connector"].sudo()
        cfg = connector._get_config_settings()
        token = cfg["listing_api_key"] or cfg["api_key"]
        for listing in self.filtered("bayut_external_id"):
            listing._bayut_refresh_one(connector, token)
        return True


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bayut_default_bayut_user_id = fields.Char(
        string="Default Bayut Agent ID",
        config_parameter="bayut_lead_integration.bayut_default_bayut_user_id",
        help="Bayut user ID used when a listing's agent has no Bayut account "
             "(Test Connection fills it in when your agency has one Bayut user).",
    )
