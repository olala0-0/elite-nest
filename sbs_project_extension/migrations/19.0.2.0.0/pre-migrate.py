from odoo.exceptions import ValidationError


DETAIL_COLUMNS = (
    'id',
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
    'proposed_value',
    'locked_value',
    'revised_value',
)


def migrate(cr, version):
    orphan_counts = {}
    for table, label in (
        ('sbs_project_extension_collection_plan', 'collection plans'),
        ('sbs_project_extension_collection_history', 'collection history'),
    ):
        cr.execute("SELECT to_regclass(%s)", (table,))
        if not cr.fetchone()[0]:
            continue
        cr.execute(
            f"SELECT COUNT(*) FROM {table} WHERE project_id IS NULL"
        )
        count = cr.fetchone()[0]
        if count:
            orphan_counts[label] = count

    if orphan_counts:
        details = ', '.join(
            f"{label}: {count}"
            for label, count in orphan_counts.items()
        )
        raise ValidationError(
            "SBS Project Extension cannot be upgraded while project-less "
            f"financial records exist ({details}). Assign a project to "
            "those records and retry the upgrade."
        )

    cr.execute(
        "DROP TABLE IF EXISTS "
        "pg_temp.sbs_project_extension_detail_migration"
    )
    cr.execute(
        "CREATE TEMP TABLE sbs_project_extension_detail_migration "
        "ON COMMIT DROP AS SELECT "
        f"{', '.join(DETAIL_COLUMNS)} FROM project_project"
    )
