from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    hidden_menu_ids = fields.Many2many(
        comodel_name="ir.ui.menu",
        relation="eg_user_hidden_menu_rel",
        column1="user_id",
        column2="menu_id",
        string="Hidden Menus",
        groups="base.group_system",
        help="Menus (and all their sub-menus) that will be hidden for this user.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if any("hidden_menu_ids" in vals for vals in vals_list):
            self.env.registry.clear_cache()
        return users

    def write(self, vals):
        res = super().write(vals)
        if "hidden_menu_ids" in vals:
            # Menus are cached per user; refresh so the change applies immediately.
            self.env.registry.clear_cache()
        return res

