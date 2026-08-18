from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """A leftover Studio-created view (never exported to this repo, so it
    only exists in each database independently) references
    x_studio_security_deposit, a Studio custom field that fails to
    register - any view still holding that reference blocks the entire
    registry from loading with "Field ... does not exist in model
    rent.contract". Deletes any view still carrying that stale reference,
    in whichever database this migration runs against, instead of relying
    on a one-off manual per-environment fix via the Studio UI."""
    cr.execute("""
        SELECT id FROM ir_ui_view
        WHERE arch_db::text LIKE '%x_studio_security_deposit%'
    """)
    view_ids = [row[0] for row in cr.fetchall()]
    if view_ids:
        env = api.Environment(cr, SUPERUSER_ID, {})
        env['ir.ui.view'].browse(view_ids).unlink()
