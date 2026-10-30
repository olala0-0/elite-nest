from odoo import SUPERUSER_ID, api
from odoo.tools import SQL


CREDENTIAL_FIELDS = (
    'prod_hosting',
    'prod_link',
    'prod_db',
    'prod_user',
    'prod_pass',
    'prod_master_pass',
    'prod_server_ip',
    'prod_server_user',
    'prod_server_password',
    'prod_server_os',
    'stag_hosting',
    'stag_link',
    'stag_db',
    'stag_user',
    'stag_pass',
    'stag_master_pass',
    'stag_server_ip',
    'stag_server_user',
    'stag_server_password',
    'stag_server_os',
)

FINANCIAL_FIELDS = (
    'proposed_value',
    'locked_value',
    'revised_value',
)


def _copy_project_columns(env, model_name, field_names):
    Detail = env['project.project']._sbs_get_detail_model(model_name)
    existing_project_ids = set(
        Detail.search([]).project_id.ids
    )

    columns = ('id', *field_names)
    env.cr.execute(SQL(
        "SELECT %s FROM sbs_project_extension_detail_migration",
        SQL(', ').join(SQL.identifier(column) for column in columns),
    ))
    values_list = []
    for row in env.cr.fetchall():
        project_id, *values = row
        if project_id in existing_project_ids:
            continue
        values_list.append({
            'project_id': project_id,
            **dict(zip(field_names, values)),
        })
    if values_list:
        Detail.create(values_list)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _copy_project_columns(
        env,
        'sbs_project_extension.project.credentials',
        CREDENTIAL_FIELDS,
    )
    _copy_project_columns(
        env,
        'sbs_project_extension.project.financial',
        FINANCIAL_FIELDS,
    )

    env['project.project'].with_context(
        active_test=False
    ).search([])._sbs_ensure_detail_records()
    env['res.users'].with_context(
        active_test=False
    ).search([])._sbs_sync_project_team_entries()
