from odoo import api, fields, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    hidden_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="eg_user_hidden_menu_rel",
        column1="menu_id",
        column2="user_id",
        string="Hidden for Users",
        groups="base.group_system",
        help="This menu (and all its sub-menus) will be hidden for these users.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        menus = super().create(vals_list)
        if any("hidden_user_ids" in vals for vals in vals_list):
            self.env.registry.clear_cache()
        return menus

    def write(self, vals):
        res = super().write(vals)
        if "hidden_user_ids" in vals:
            self.env.registry.clear_cache()
        return res

    def _filter_visible_menus(self):
        """Apply the standard group-based filtering, then remove the menus
        the current user has been configured to not see (with their children)."""
        menus = super()._filter_visible_menus()
        if self.env.su or not menus:
            return menus
        hidden = self.env.user.sudo().hidden_menu_ids
        if not hidden:
            return menus
        # sudo() avoids re-entering this filter through search()
        hidden_ids = set(
            self.sudo().with_context(active_test=False)
            .search([("id", "child_of", hidden.ids)]).ids
        )
        return menus.filtered(lambda m: m.id not in hidden_ids)

