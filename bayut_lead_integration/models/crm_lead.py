# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    bayut_lead_id = fields.Char(
        string="Bayut Lead ID",
        index=True,
        copy=False,
        readonly=True,
        help="Unique external lead identifier received from the Bayut Leads API.",
    )
    bayut_lead_type = fields.Char(
        string="Bayut Lead Type",
        index=True,
        copy=False,
        help="Lead channel/type from Bayut (e.g., email, call_log, phone_view, whatsapp, sms_click, whatsapp_view).",
    )
    bayut_property_ref = fields.Char(
        string="Bayut Property Reference",
        index=True,
        copy=False,
        help="Property reference code associated with the Bayut listing.",
    )
    bayut_listing_id = fields.Many2one(
        comodel_name="bayut.listing",
        string="Bayut Listing",
        index=True,
        ondelete="set null",
        help="Linked Bayut listing record in Odoo.",
    )

    _sql_constraints = [
        (
            "bayut_lead_id_unique",
            "unique(bayut_lead_id)",
            "A CRM Lead with this Bayut Lead ID already exists!",
        ),
    ]

    @api.constrains("bayut_lead_id")
    def _check_unique_bayut_lead_id(self):
        for lead in self:
            if not lead.bayut_lead_id:
                continue
            duplicate = self.sudo().search(
                [
                    ("bayut_lead_id", "=", lead.bayut_lead_id),
                    ("id", "!=", lead.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("A CRM Lead with Bayut Lead ID '%s' already exists.") % lead.bayut_lead_id
                )
