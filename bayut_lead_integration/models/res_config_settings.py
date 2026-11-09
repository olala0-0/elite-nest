# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bayut_api_url = fields.Char(
        string="Bayut API URL",
        default="https://leads-api.bayut.com/",
        config_parameter="bayut_lead_integration.bayut_api_url",
        help="Endpoint URL for the Bayut Leads API. Update this with the production URL provided by Bayut Support.",
    )
    bayut_api_key = fields.Char(
        string="Bayut API Key",
        config_parameter="bayut_lead_integration.bayut_api_key",
        help="Bearer API token provided by Bayut Support.",
    )
    bayut_default_team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Default Sales Team",
        config_parameter="bayut_lead_integration.bayut_default_team_id",
        help="Sales team automatically assigned to newly imported Bayut leads.",
    )
    bayut_default_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Default Salesperson",
        config_parameter="bayut_lead_integration.bayut_default_user_id",
        domain=[("share", "=", False)],
        help="Salesperson automatically assigned to newly imported Bayut leads.",
    )
    bayut_sync_interval = fields.Integer(
        string="Sync Interval (Minutes)",
        default=10,
        config_parameter="bayut_lead_integration.bayut_sync_interval",
        help="Frequency in minutes for the 'Bayut: Sync Leads' scheduled action.",
    )
    bayut_last_sync = fields.Datetime(
        string="Last Successful Sync",
        compute="_compute_bayut_sync_info",
        readonly=True,
    )
    bayut_sync_log_count = fields.Integer(
        string="Bayut Sync Logs Count",
        compute="_compute_bayut_sync_info",
        readonly=True,
    )
    bayut_recent_log_ids = fields.Many2many(
        comodel_name="bayut.sync.log",
        string="Recent Bayut Sync Logs",
        compute="_compute_bayut_sync_info",
        readonly=True,
    )

    def _compute_bayut_sync_info(self):
        connector = self.env["bayut.connector"].sudo()._get_connector()
        recent_logs = self.env["bayut.sync.log"].sudo().search([], limit=10)
        total_logs = self.env["bayut.sync.log"].sudo().search_count([])
        for record in self:
            record.bayut_last_sync = connector.last_sync
            record.bayut_sync_log_count = total_logs
            record.bayut_recent_log_ids = recent_logs

    def set_values(self):
        super().set_values()
        interval = max(int(self.bayut_sync_interval or 10), 1)
        cron = self.env.ref(
            "bayut_lead_integration.ir_cron_bayut_sync_leads",
            raise_if_not_found=False,
        )
        if cron:
            cron.sudo().write({
                "interval_number": interval,
                "interval_type": "minutes",
            })

    def action_bayut_test_connection(self):
        """Save current settings and test the Bayut API connection."""
        self.ensure_one()
        self.set_values()
        result = self.env["bayut.connector"].test_api_connection()
        is_ok = bool(result.get("success"))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Bayut Connection Successful") if is_ok else _("Bayut Connection Failed"),
                "message": result.get("message", ""),
                "type": "success" if is_ok else "warning",
                "sticky": not is_ok,
            },
        }

    def action_bayut_sync_now(self):
        """Save current settings and run the Bayut lead synchronization immediately."""
        self.ensure_one()
        self.set_values()
        result = self.env["bayut.connector"].cron_sync_leads()
        is_ok = result.get("status") == "success"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Bayut Manual Sync"),
                "message": result.get("message", ""),
                "type": "success" if is_ok else "warning",
                "sticky": not is_ok,
            },
        }

    def action_open_bayut_sync_logs(self):
        """Smart button action in Settings to view all Bayut sync logs."""
        self.ensure_one()
        return {
            "name": _("Bayut Sync Logs"),
            "type": "ir.actions.act_window",
            "res_model": "bayut.sync.log",
            "view_mode": "list,form",
            "target": "current",
        }
