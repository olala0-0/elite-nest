# -*- coding: utf-8 -*-
from odoo import fields, models


class BayutSyncLog(models.Model):
    _name = "bayut.sync.log"
    _description = "Bayut Lead Sync Log"
    _order = "sync_datetime desc, id desc"
    _rec_name = "sync_datetime"

    connector_id = fields.Many2one(
        comodel_name="bayut.connector",
        string="Bayut Connector",
        ondelete="cascade",
        readonly=True,
    )
    sync_datetime = fields.Datetime(
        string="Sync Date & Time",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        index=True,
    )
    status = fields.Selection(
        selection=[
            ("success", "Success"),
            ("error", "Error"),
        ],
        string="Status",
        required=True,
        default="success",
        readonly=True,
        index=True,
    )
    leads_created = fields.Integer(
        string="Leads Created",
        default=0,
        readonly=True,
    )
    message = fields.Text(
        string="Details / Message",
        readonly=True,
    )
