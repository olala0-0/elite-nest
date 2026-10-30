from . import models
from . import wizard


def post_init_hook(env):
    env['project.project'].with_context(
        active_test=False
    ).search([])._sbs_ensure_detail_records()
    env['res.users'].with_context(
        active_test=False
    ).search([])._sbs_sync_project_team_entries()
