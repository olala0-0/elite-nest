from odoo import Command, SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    project_user = env.ref(
        'sbs_project_extension.group_sbs_project_extension'
    )
    credentials_user = env.ref(
        'sbs_project_extension.group_sbs_project_password_user'
    )
    financial_user = env.ref(
        'sbs_project_extension.group_sbs_project_financial_user'
    )
    combined_user = env.ref(
        'sbs_project_extension.group_sbs_project_credentials_financial_user'
    )
    previous_roles = project_user | credentials_user | financial_user

    users = env['res.users'].with_context(active_test=False).search([
        ('group_ids', 'in', previous_roles.ids),
    ])
    for user in users:
        explicit_roles = user.group_ids & previous_roles
        if credentials_user in explicit_roles and financial_user in explicit_roles:
            selected_role = combined_user
        elif credentials_user in explicit_roles:
            selected_role = credentials_user
        elif financial_user in explicit_roles:
            selected_role = financial_user
        else:
            selected_role = project_user

        user.write({
            'group_ids': [
                *(Command.unlink(group.id) for group in explicit_roles),
                Command.link(selected_role.id),
            ],
        })
