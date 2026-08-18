from ast import literal_eval

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSbsProjectExtension(TransactionCase):

    def _assert_fields_no_open(self, view_xml_id, field_names):
        view = self.env.ref(view_xml_id)
        arch = etree.fromstring(view.arch_db.encode())

        for field_name in field_names:
            nodes = arch.xpath(f"//field[@name='{field_name}']")
            self.assertTrue(nodes, field_name)
            for node in nodes:
                options = literal_eval(node.get('options', '{}'))
                self.assertTrue(options.get('no_open'), field_name)

    def _create_user(self, login, group):
        return self.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': login,
            'login': login,
            'group_ids': [Command.set(group.ids)],
        })

    def test_review_copy_preserves_all_review_flags(self):
        project = self.env['project.project'].create({
            'name': 'SBS Review Copy Project',
        })
        review = self.env['sbs_project_extension.review.session'].create({
            'name': 'SBS Review Copy',
            'review_line_ids': [(0, 0, {
                'project_id': project.id,
                'task_frozen': 'yes',
                'customer_task_frozen': 'no',
            })],
        })

        copied_line = review.copy().review_line_ids

        self.assertEqual(copied_line.task_frozen, 'yes')
        self.assertEqual(copied_line.customer_task_frozen, 'no')

    def test_project_details_follow_project_access(self):
        company_a = self.env.company
        company_b = self.env['res.company'].create({
            'name': 'SBS Project Test Company B',
        })
        financial_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_financial_user'
        )
        user = self.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': 'SBS Project Details User',
            'login': 'sbs_project_details_user',
            'company_id': company_a.id,
            'company_ids': [Command.set(company_a.ids)],
            'group_ids': [Command.set(financial_group.ids)],
        })
        project_a = self.env['project.project'].create({
            'name': 'Accessible Project',
            'company_id': company_a.id,
            'privacy_visibility': 'employees',
        })
        project_b = self.env['project.project'].with_company(company_b).create({
            'name': 'Restricted Project',
            'company_id': company_b.id,
            'privacy_visibility': 'followers',
        })
        plan_a = self.env['sbs_project_extension.collection.plan'].create({
            'project_id': project_a.id,
            'milestone': 'Accessible Milestone',
        })
        plan_b = self.env[
            'sbs_project_extension.collection.plan'
        ].with_company(company_b).create({
            'project_id': project_b.id,
            'milestone': 'Restricted Milestone',
        })
        review = self.env['sbs_project_extension.review.session'].create({
            'name': 'SBS Access Review',
            'review_line_ids': [Command.create({'project_id': project_a.id})],
        })
        review_b = self.env[
            'sbs_project_extension.review.line'
        ].with_company(company_b).create({
            'review_id': review.id,
            'project_id': project_b.id,
        })
        review_a = review.review_line_ids.filtered(
            lambda line: line.project_id == project_a
        )
        project_b.active = False

        self.assertFalse(
            self.env['project.project'].with_user(user).search([
                ('id', '=', project_b.id),
            ])
        )
        self.assertEqual(
            self.env['sbs_project_extension.collection.plan'].with_user(
                user
            ).search([('id', 'in', (plan_a | plan_b).ids)]),
            plan_a,
        )
        self.assertEqual(
            self.env['sbs_project_extension.review.line'].with_user(
                user
            ).search([('id', 'in', (review_a | review_b).ids)]),
            review_a,
        )
        with self.assertRaises(AccessError):
            plan_b.with_user(user).read(['milestone'])
        with self.assertRaises(AccessError):
            review_b.with_user(user).read(['internal_review'])
        with self.assertRaises(AccessError):
            self.env['sbs_project_extension.collection.plan'].with_user(
                user
            ).create({
                'project_id': project_b.id,
                'milestone': 'Blocked Milestone',
            })
        self.assertFalse(
            self.env['sbs_project_extension.review.session'].with_user(
                user
            ).search([('id', '=', review.id)])
        )
        with self.assertRaises(AccessError):
            review.with_user(user).read(['name'])
        with self.assertRaises(AccessError):
            review.with_user(user).unlink()

    def test_credential_fields_are_visible_char_fields(self):
        view = self.env.ref(
            'sbs_project_extension.'
            'view_sbs_project_extension_form_custom'
        )
        arch = etree.fromstring(view.arch_db.encode())

        for field_name in (
            'prod_pass',
            'prod_master_pass',
            'prod_server_password',
            'stag_pass',
            'stag_master_pass',
            'stag_server_password',
        ):
            nodes = arch.xpath(f"//field[@name='{field_name}']")
            self.assertTrue(nodes, field_name)
            self.assertIsNone(nodes[0].get('password'))
            self.assertEqual(
                self.env['project.project']._fields[field_name].type,
                'char',
            )

    def test_custom_relational_fields_cannot_open_linked_records(self):
        self._assert_fields_no_open(
            'sbs_project_extension.view_sbs_project_extension_form_custom',
            (
                'risk_factor_id',
                'review_id',
                'sp_ids',
                'pm_ids',
                'developer_ids',
                'qa_ids',
                'fa_ids',
                'pc_ids',
                'kam_ids',
                'csm_ids',
                'industry_id',
                'client_country_id',
                'tech_stack_id',
                'responsible_id',
                'collected_by_id',
            ),
        )
        self._assert_fields_no_open(
            'sbs_project_extension.'
            'view_sbs_project_extension_review_session_form',
            ('project_id', 'sp_ids', 'fa_ids', 'pc_ids'),
        )

        for view_xml_id, field_names in (
            (
                'sbs_project_extension.'
                'view_sbs_project_extension_form_custom',
                (
                    'review_line_ids',
                    'collection_plan_ids',
                    'collection_history_ids',
                ),
            ),
            (
                'sbs_project_extension.'
                'view_sbs_project_extension_review_session_form',
                ('review_line_ids',),
            ),
        ):
            view = self.env.ref(view_xml_id)
            arch = etree.fromstring(view.arch_db.encode())
            for field_name in field_names:
                lists = arch.xpath(
                    f"//field[@name='{field_name}']/list"
                )
                self.assertTrue(lists, field_name)
                self.assertEqual(lists[0].get('no_open'), '1')

    def test_project_form_lock_and_native_no_open_configuration(self):
        project_view = self.env.ref('project.edit_project')
        arch, _view = self.env['project.project']._get_view(
            project_view.id,
            'form',
        )

        for field_name in (
            'tag_ids',
            'user_id',
            'account_id',
            'responsible_id',
        ):
            nodes = arch.xpath(f"//field[@name='{field_name}']")
            self.assertTrue(nodes, field_name)
            self.assertTrue(
                any(
                    literal_eval(node.get('options', '{}')).get('no_open')
                    for node in nodes
                ),
                field_name,
            )

        for page_name in (
            'description',
            'settings',
            'sbs_summary',
            'sbs_team',
            'sbs_client_details',
            'sbs_technical_info',
            'sbs_amc_details',
            'sbs_credentials',
            'sbs_financials',
        ):
            pages = arch.xpath(f"//page[@name='{page_name}']")
            self.assertTrue(pages, page_name)
            self.assertEqual(pages[0].get('readonly'), 'sbs_is_locked')

        for button_name in ('action_sbs_lock', 'action_sbs_unlock'):
            buttons = arch.xpath(f"//button[@name='{button_name}']")
            self.assertTrue(buttons, button_name)
            self.assertEqual(
                buttons[0].get('groups'),
                'base.group_system',
            )

        processed_arch = etree.fromstring(
            self.env['project.project'].get_view(
                project_view.id,
                'form',
            )['arch'].encode()
        )
        project_field_nodes = [
            node
            for node in processed_arch.iter('field')
            if not any(
                ancestor.tag in ('button', 'field')
                for ancestor in node.iterancestors()
            )
        ]
        for node in project_field_nodes:
            if node.get('name') == 'sbs_is_locked':
                continue
            readonly = node.get('readonly')
            self.assertTrue(
                readonly in ('1', 'True')
                or 'sbs_is_locked' in (readonly or ''),
                node.get('name'),
            )

    def test_only_super_admin_can_lock_and_locked_project_is_immutable(self):
        project_admin_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_admin'
        )
        project_admin = self._create_user(
            'sbs_project_lock_admin', project_admin_group
        )
        super_admin = self._create_user(
            'sbs_project_lock_super_admin',
            project_admin_group | self.env.ref('base.group_system'),
        )
        project = self.env['project.project'].create({
            'name': 'SBS Lock Test Project',
            'privacy_visibility': 'employees',
        })
        collection_plan = self.env[
            'sbs_project_extension.collection.plan'
        ].create({
            'project_id': project.id,
            'milestone': 'Initial milestone',
        })
        review = self.env['sbs_project_extension.review.session'].create({
            'name': 'SBS Lock Test Review',
            'review_line_ids': [Command.create({
                'project_id': project.id,
                'internal_review': 'Initial review',
            })],
        })
        review_line = review.review_line_ids

        with self.assertRaises(AccessError):
            project.with_user(project_admin).action_sbs_lock()

        project.with_user(super_admin).action_sbs_lock()
        self.assertTrue(project.sbs_is_locked)

        for user in project_admin | super_admin:
            with self.assertRaises(UserError):
                project.with_user(user).write({
                    'next_action': 'Blocked while locked',
                })
        with self.assertRaises(UserError):
            project.with_user(project_admin).sudo().write({
                'next_action': 'Blocked sudo write',
            })
        with self.assertRaises(UserError):
            project.with_user(super_admin).with_context(
                import_file=True
            ).write({'next_action': 'Blocked import'})
        with self.assertRaises(UserError):
            project.with_user(super_admin).unlink()
        with self.assertRaises(AccessError):
            project.with_user(super_admin).write({
                'sbs_is_locked': False,
            })

        with self.assertRaises(UserError):
            collection_plan.with_user(super_admin).write({
                'milestone': 'Blocked milestone',
            })
        with self.assertRaises(UserError):
            collection_plan.with_user(super_admin).unlink()
        with self.assertRaises(UserError):
            self.env[
                'sbs_project_extension.collection.plan'
            ].with_user(super_admin).create({
                'project_id': project.id,
                'milestone': 'Blocked new milestone',
            })
        with self.assertRaises(UserError):
            review_line.with_user(super_admin).write({
                'internal_review': 'Blocked review',
            })
        with self.assertRaises(UserError):
            review.with_user(super_admin).write({
                'name': 'Blocked review session',
            })
        with self.assertRaises(UserError):
            review.with_user(super_admin).unlink()

        with self.assertRaises(AccessError):
            project.with_user(project_admin).action_sbs_unlock()
        with self.assertRaises(AccessError):
            project.with_user(project_admin).sudo().action_sbs_unlock()

        project.with_user(super_admin).action_sbs_unlock()
        self.assertFalse(project.sbs_is_locked)
        project.with_user(super_admin).write({
            'next_action': 'Allowed after unlock',
        })
        collection_plan.with_user(super_admin).write({
            'milestone': 'Allowed after unlock',
        })
        self.assertEqual(project.next_action, 'Allowed after unlock')
        self.assertEqual(
            collection_plan.milestone,
            'Allowed after unlock',
        )

    def test_password_and_financial_visibility_groups(self):
        extension_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_extension'
        )
        password_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_password_user'
        )
        financial_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_financial_user'
        )
        combined_group = self.env.ref(
            'sbs_project_extension.'
            'group_sbs_project_credentials_financial_user'
        )
        admin_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_admin'
        )
        privilege = self.env.ref(
            'sbs_project_extension.privilege_sbs_project_role'
        )
        role_groups = (
            extension_group
            | password_group
            | financial_group
            | combined_group
            | admin_group
        )
        self.assertEqual(role_groups.privilege_id, privilege)
        self.assertIn(extension_group, password_group.implied_ids)
        self.assertIn(extension_group, financial_group.implied_ids)
        self.assertIn(password_group, combined_group.implied_ids)
        self.assertIn(financial_group, combined_group.implied_ids)
        self.assertIn(combined_group, admin_group.implied_ids)

        extension_user = self._create_user(
            'sbs_project_extension_user', extension_group
        )
        password_user = self._create_user(
            'sbs_project_password_user', password_group
        )
        financial_user = self._create_user(
            'sbs_project_financial_user', financial_group
        )
        combined_user = self._create_user(
            'sbs_project_credentials_financial_user', combined_group
        )
        admin_user = self._create_user(
            'sbs_project_admin', admin_group
        )

        project_model = self.env['project.project']
        self.assertNotIn(
            'prod_pass', project_model.with_user(extension_user).fields_get()
        )
        self.assertNotIn(
            'proposed_value',
            project_model.with_user(extension_user).fields_get(),
        )
        self.assertIn(
            'prod_pass', project_model.with_user(password_user).fields_get()
        )
        self.assertNotIn(
            'proposed_value',
            project_model.with_user(password_user).fields_get(),
        )
        self.assertIn(
            'proposed_value',
            project_model.with_user(financial_user).fields_get(),
        )
        self.assertNotIn(
            'prod_pass', project_model.with_user(financial_user).fields_get()
        )
        for user in combined_user | admin_user:
            self.assertIn(
                'prod_pass', project_model.with_user(user).fields_get()
            )
            self.assertIn(
                'proposed_value', project_model.with_user(user).fields_get()
            )

        credentials_view = self.env.ref(
            'sbs_project_extension.'
            'view_sbs_project_extension_credentials_list'
        )
        financials_view = self.env.ref(
            'sbs_project_extension.'
            'view_sbs_project_extension_financials_list'
        )
        self.assertEqual(credentials_view.group_ids, password_group)
        self.assertEqual(financials_view.group_ids, financial_group)

        credentials_menu = self.env.ref(
            'sbs_project_extension.'
            'menu_sbs_project_extension_credentials'
        )
        financials_menu = self.env.ref(
            'sbs_project_extension.'
            'menu_sbs_project_extension_financials'
        )
        self.assertEqual(credentials_menu.group_ids, password_group)
        self.assertEqual(financials_menu.group_ids, financial_group)

        with self.assertRaises(ValidationError):
            extension_user.write({
                'group_ids': [Command.set(
                    (password_group | financial_group).ids
                )],
            })

        task_read_create_group = self.env.ref(
            'sbs_project_extension.group_sbs_task_read_create'
        )
        self.assertNotEqual(
            task_read_create_group.privilege_id,
            privilege,
        )
        password_user.write({
            'group_ids': [Command.set(
                (password_group | task_read_create_group).ids
            )],
        })
        self.assertIn(task_read_create_group, password_user.group_ids)
        self.assertIn(password_group, password_user.group_ids)

    def test_dedicated_credential_and_financial_details(self):
        password_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_password_user'
        )
        financial_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_financial_user'
        )
        extension_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_extension'
        )
        password_user = self._create_user(
            'sbs_detail_password_user', password_group
        )
        financial_user = self._create_user(
            'sbs_detail_financial_user', financial_group
        )
        extension_user = self._create_user(
            'sbs_detail_extension_user', extension_group
        )
        project = self.env['project.project'].create({
            'name': 'SBS Dedicated Detail Project',
            'privacy_visibility': 'employees',
            'prod_hosting': 'initial-production-host',
            'proposed_value': 750.0,
        })

        self.assertEqual(len(project.credential_detail_ids), 1)
        self.assertEqual(len(project.financial_detail_ids), 1)
        credentials = project.credential_detail_ids
        financials = project.financial_detail_ids
        self.assertEqual(credentials.prod_hosting, 'initial-production-host')
        self.assertEqual(financials.proposed_value, 750.0)

        credentials.with_user(password_user).write({
            'prod_pass': 'visible-by-design',
        })
        financials.with_user(financial_user).write({
            'proposed_value': 1250.0,
        })
        project.invalidate_recordset()
        self.assertEqual(project.prod_pass, 'visible-by-design')
        self.assertEqual(project.proposed_value, 1250.0)
        self.assertEqual(financials.currency_id, project.currency_id)

        with self.assertRaises(AccessError):
            credentials.with_user(extension_user).read(['prod_pass'])
        with self.assertRaises(AccessError):
            financials.with_user(password_user).read(['proposed_value'])
        with self.assertRaises(AccessError):
            self.env[
                'sbs_project_extension.project.credentials'
            ].with_user(password_user).create({
                'project_id': project.id,
            })

        project.action_sbs_lock()
        with self.assertRaises(UserError):
            credentials.with_user(password_user).write({
                'prod_pass': 'blocked-while-locked',
            })
        with self.assertRaises(UserError):
            financials.with_user(financial_user).write({
                'proposed_value': 2000.0,
            })
        project.action_sbs_unlock()

    def test_general_sbs_fields_are_restricted_at_orm_level(self):
        project_user = self._create_user(
            'sbs_plain_project_user',
            self.env.ref('project.group_project_user'),
        )
        field_names = self.env['project.project'].with_user(
            project_user
        ).fields_get()

        for field_name in (
            'risk_level',
            'fa_ids',
            'team_formation_type',
            'client_name',
            'amc_status',
        ):
            self.assertNotIn(field_name, field_names)
        self.assertIn('sbs_priority_number', field_names)
        self.assertIn('sbs_project_director', field_names)

    def test_read_task_only_and_admin_task_permissions(self):
        read_task_user = self._create_user(
            'sbs_read_task_only_user',
            self.env.ref(
                'sbs_project_extension.group_sbs_task_read_create'
            ),
        )
        regular_task_user = self._create_user(
            'sbs_regular_task_user',
            self.env.ref('project.group_project_user'),
        )
        project_admin = self._create_user(
            'sbs_task_project_admin',
            self.env.ref(
                'sbs_project_extension.group_sbs_project_admin'
            ),
        )
        project = self.env['project.project'].create({
            'name': 'SBS Follower Task Project',
            'privacy_visibility': 'followers',
        })
        project.message_subscribe(
            (read_task_user | regular_task_user).partner_id.ids
        )

        read_task = self.env['project.task'].with_user(
            read_task_user
        ).with_context(default_project_id=project.id).create({
            'name': 'Created by read task user',
            'project_id': project.id,
        })
        with self.assertRaises(AccessError):
            read_task.with_user(read_task_user).write({
                'name': 'Blocked edit',
            })
        with self.assertRaises(AccessError):
            read_task.with_user(read_task_user).unlink()

        extra_follower = self.env['res.partner'].create({
            'name': 'SBS Read Task Extra Follower',
        })
        read_task.with_user(read_task_user).message_subscribe(
            extra_follower.ids
        )
        self.assertIn(extra_follower, read_task.message_partner_ids)
        message = read_task.with_user(read_task_user).message_post(
            body='Read Task Only comment remains allowed.',
        )
        self.assertTrue(message.exists())
        activity = read_task.with_user(read_task_user).activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=read_task_user.id,
            summary='Read Task Only activity remains allowed',
        )
        self.assertTrue(activity.exists())

        regular_task = self.env['project.task'].with_user(
            regular_task_user
        ).with_context(default_project_id=project.id).create({
            'name': 'Regular follower task',
            'project_id': project.id,
        })
        regular_task.with_user(regular_task_user).write({
            'name': 'Regular follower edit allowed',
        })
        with self.assertRaises(AccessError):
            regular_task.with_user(regular_task_user).unlink()

        (read_task | regular_task).with_user(project_admin).unlink()
        self.assertFalse((read_task | regular_task).exists())

        task_form = self.env.ref('project.view_task_form2')
        read_arch, _view = self.env['project.task'].with_user(
            read_task_user
        )._get_view(task_form.id, 'form')
        self.assertEqual(read_arch.get('edit'), 'false')
        self.assertEqual(read_arch.get('delete'), 'false')
        self.assertNotEqual(read_arch.get('create'), 'false')

        admin_arch, _view = self.env['project.task'].with_user(
            project_admin
        )._get_view(task_form.id, 'form')
        self.assertNotEqual(admin_arch.get('delete'), 'false')

    def test_only_sbs_admin_can_create_or_delete_projects(self):
        standard_manager = self._create_user(
            'sbs_standard_project_manager',
            self.env.ref('project.group_project_manager'),
        )
        project_admin = self._create_user(
            'sbs_project_create_admin',
            self.env.ref(
                'sbs_project_extension.group_sbs_project_admin'
            ),
        )

        with self.assertRaises(AccessError):
            self.env['project.project'].with_user(
                standard_manager
            ).create({'name': 'Blocked manual project'})
        with self.assertRaises(AccessError):
            self.env['project.project'].with_user(
                standard_manager
            ).with_context(import_file=True).create({
                'name': 'Blocked imported project',
            })
        trusted_project = self.env['project.project'].with_user(
            standard_manager
        ).sudo().create({'name': 'Trusted automated project'})
        self.assertTrue(trusted_project.exists())

        project = self.env['project.project'].with_user(
            project_admin
        ).create({'name': 'SBS Admin Project'})
        with self.assertRaises(AccessError):
            project.with_user(standard_manager).unlink()

        project_list = self.env.ref('project.view_project')
        manager_arch, _view = self.env['project.project'].with_user(
            standard_manager
        )._get_view(project_list.id, 'list')
        self.assertEqual(manager_arch.get('create'), 'false')
        self.assertEqual(manager_arch.get('delete'), 'false')

        admin_arch, _view = self.env['project.project'].with_user(
            project_admin
        )._get_view(project_list.id, 'list')
        self.assertNotEqual(admin_arch.get('create'), 'false')
        self.assertNotEqual(admin_arch.get('delete'), 'false')

        project.with_user(project_admin).unlink()
        self.assertFalse(project.exists())
        trusted_project.unlink()

    def test_project_priority_director_views_and_ordering(self):
        project_zero = self.env['project.project'].create({
            'name': 'SBS Priority Zero',
            'sbs_priority_number': 0,
        })
        project_two = self.env['project.project'].create({
            'name': 'SBS Priority Two',
            'sbs_priority_number': 2,
        })
        project_one = self.env['project.project'].create({
            'name': 'SBS Priority One',
            'sbs_priority_number': 1,
        })
        projects = project_zero | project_two | project_one
        ordered = self.env['project.project'].search([
            ('id', 'in', projects.ids),
        ])
        self.assertEqual(
            ordered.ids,
            (project_one | project_two | project_zero).ids,
        )
        with self.assertRaises(ValidationError):
            project_one.write({'sbs_priority_number': -1})

        project_kanban = self.env.ref('project.view_project_kanban')
        kanban_arch, _view = self.env['project.project']._get_view(
            project_kanban.id,
            'kanban',
        )
        self.assertTrue(
            kanban_arch.get('default_order').startswith(
                'sbs_priority_number asc'
            )
        )
        self.assertTrue(
            kanban_arch.xpath("//field[@name='sbs_priority_number']")
        )

        project_form = self.env.ref('project.edit_project')
        form_arch, _view = self.env['project.project']._get_view(
            project_form.id,
            'form',
        )
        director = form_arch.xpath(
            "//sheet//field[@name='sbs_project_director']"
        )[0]
        manager = form_arch.xpath(
            "//sheet//field[@name='user_id']"
        )[0]
        self.assertLess(
            director.getparent().index(director),
            manager.getparent().index(manager),
        )

        simplified_form = self.env.ref(
            'project.project_project_view_form_simplified'
        )
        simplified_arch, _view = self.env['project.project']._get_view(
            simplified_form.id,
            'form',
        )
        self.assertTrue(simplified_arch.xpath(
            "//field[@name='sbs_project_director']"
        ))
        simplified_manager = simplified_arch.xpath(
            "//field[@name='user_id']"
        )[0]
        self.assertNotEqual(simplified_manager.get('invisible'), '1')

        master_menu = self.env.ref(
            'sbs_project_extension.'
            'menu_sbs_project_extension_master_root'
        )
        self.assertEqual(master_menu.sequence, 3)

    def test_internal_and_hybrid_team_formation(self):
        extension_group = self.env.ref(
            'sbs_project_extension.group_sbs_project_extension'
        )
        internal_user = self._create_user(
            'sbs_internal_team_user', extension_group
        )
        internal_entry = self.env[
            'sbs_project_extension.project.team'
        ].with_context(active_test=False).search([
            ('user_id', '=', internal_user.id),
        ])
        self.assertEqual(len(internal_entry), 1)
        self.assertTrue(internal_entry.active)

        external_entry = self.env[
            'sbs_project_extension.project.team'
        ].create({'name': 'External Hybrid Member'})
        project = self.env['project.project'].create({
            'name': 'SBS Hybrid Team Project',
            'team_formation_type': 'hybrid',
            'fa_ids': [Command.set(external_entry.ids)],
        })
        with self.assertRaises(ValidationError):
            project.write({'team_formation_type': 'internal'})

        project.write({
            'team_formation_type': 'internal',
            'fa_ids': [Command.set(internal_entry.ids)],
            'pc_ids': [Command.set(internal_entry.ids)],
        })
        self.assertEqual(project.pc_ids, internal_entry)
        with self.assertRaises(ValidationError):
            project.write({
                'pc_ids': [Command.set(external_entry.ids)],
            })

        internal_user.write({'name': 'Renamed Internal Team User'})
        self.assertEqual(
            internal_entry.name,
            'Renamed Internal Team User',
        )
        with self.assertRaises(AccessError):
            internal_entry.with_user(internal_user).unlink()
        with self.assertRaises(AccessError):
            self.env[
                'sbs_project_extension.project.team'
            ].with_user(internal_user).create({
                'name': 'Manual Internal Link',
                'user_id': internal_user.id,
            })

        project_form = self.env.ref(
            'sbs_project_extension.'
            'view_sbs_project_extension_form_custom'
        )
        arch = etree.fromstring(project_form.arch_db.encode())
        self.assertTrue(arch.xpath(
            "//page[@name='sbs_team']//field[@name='team_formation_type']"
        ))
        for field_name in (
            'sp_ids',
            'pm_ids',
            'developer_ids',
            'qa_ids',
            'fa_ids',
            'pc_ids',
            'kam_ids',
            'csm_ids',
        ):
            node = arch.xpath(
                f"//page[@name='sbs_team']//field[@name='{field_name}']"
            )[0]
            self.assertIn('user_id', node.get('domain', ''))

    def test_risk_decorated_lists_are_readable_without_the_sbs_group(self):
        plain_user = self._create_user(
            'sbs_project_no_group_reader',
            self.env.ref('base.group_user')
            | self.env.ref('project.group_project_user'),
        )
        self.env['project.project'].create({
            'name': 'SBS Risk Decoration Project',
            'risk_level': 'high',
        })
        Project = self.env['project.project'].with_user(plain_user)

        for view_xml_id in (
            'sbs_project_extension.view_sbs_project_extension_summary_list',
            'sbs_project_extension.view_sbs_project_extension_master_list',
        ):
            view = self.env.ref(view_xml_id)
            arch = Project.get_views([(view.id, 'list')])['views']['list']['arch']
            self.assertNotIn('risk_level', arch, view_xml_id)
            field_names = etree.fromstring(arch.encode()).xpath('//field/@name')
            Project.web_search_read(
                domain=[],
                specification={name: {} for name in set(field_names)},
                limit=5,
            )

    def test_stat_button_fields_keep_static_rendering(self):
        arch = etree.fromstring(
            self.env['project.project'].get_view(
                self.env.ref('project.edit_project').id, 'form'
            )['arch'].encode()
        )

        stat_button_fields = arch.xpath(
            "//button[contains(@class, 'oe_stat_button')]//field"
        )
        self.assertTrue(stat_button_fields)
        for node in stat_button_fields:
            self.assertNotIn(
                'sbs_is_locked',
                node.get('readonly') or '',
                node.get('name'),
            )

        sheet_field = arch.xpath("//field[@name='sbs_priority_number']")
        self.assertTrue(sheet_field)
        self.assertIn('sbs_is_locked', sheet_field[0].get('readonly') or '')

    def _team_entries(self, prefix, count=2):
        Team = self.env['sbs_project_extension.project.team']
        internal_group = self.env.ref('base.group_user')
        entries = Team.browse()
        for index in range(count):
            user = self._create_user(f'{prefix}_{index}', internal_group)
            entries |= Team.search([('user_id', '=', user.id)])
        self.assertEqual(len(entries), count)
        return entries

    def test_lead_team_members_default_to_the_first_entry(self):
        Team = self.env['sbs_project_extension.project.team']
        developers = self._team_entries('sbs_kanban_dev')
        consultants = self._team_entries('sbs_kanban_fa')
        project = self.env['project.project'].create({
            'name': 'SBS Kanban Avatar Project',
            'developer_ids': [Command.set(developers.ids)],
            'fa_ids': [Command.set(consultants.ids)],
        })

        first_developer = Team.browse(min(developers.ids))
        first_consultant = Team.browse(min(consultants.ids))
        self.assertEqual(project.sbs_lead_developer_id, first_developer)
        self.assertEqual(project.sbs_lead_fa_id, first_consultant)
        self.assertEqual(
            project.sbs_lead_developer_user_id, first_developer.user_id
        )
        self.assertEqual(
            project.sbs_lead_fa_user_id, first_consultant.user_id
        )

    def test_explicit_lead_developer_survives_and_resets_when_removed(self):
        Team = self.env['sbs_project_extension.project.team']
        developers = self._team_entries('sbs_kanban_lead_dev')
        chosen = Team.browse(max(developers.ids))
        other = Team.browse(min(developers.ids))
        project = self.env['project.project'].create({
            'name': 'SBS Kanban Lead Override Project',
            'developer_ids': [Command.set(developers.ids)],
        })

        project.sbs_lead_developer_id = chosen
        self.assertEqual(project.sbs_lead_developer_user_id, chosen.user_id)

        project.developer_ids = [Command.set(developers.ids)]
        self.assertEqual(project.sbs_lead_developer_id, chosen)

        project.developer_ids = [Command.unlink(chosen.id)]
        self.assertEqual(project.sbs_lead_developer_id, other)
        self.assertEqual(project.sbs_lead_developer_user_id, other.user_id)

    def test_lead_team_members_are_empty_without_team(self):
        project = self.env['project.project'].create({
            'name': 'SBS Kanban Empty Team Project',
        })

        self.assertFalse(project.sbs_lead_developer_id)
        self.assertFalse(project.sbs_lead_fa_id)
        self.assertFalse(project.sbs_lead_developer_user_id)
        self.assertFalse(project.sbs_lead_fa_user_id)

    def test_kanban_renders_team_avatars(self):
        general_user = self._create_user(
            'sbs_kanban_avatar_viewer',
            self.env.ref('sbs_project_extension.group_sbs_project_extension'),
        )
        arch = etree.fromstring(
            self.env['project.project'].with_user(general_user).get_view(
                self.env.ref('project.view_project_kanban').id, 'kanban'
            )['arch'].encode()
        )

        for field_name in (
            'sbs_project_director',
            'sbs_lead_fa_user_id',
            'sbs_lead_developer_user_id',
        ):
            self.assertTrue(
                arch.xpath(
                    f"//field[@name='{field_name}']"
                    "[@widget='many2one_avatar_user']"
                ),
                field_name,
            )

    def test_empty_recordset_write_and_unlink_are_not_blocked(self):
        read_task_user = self._create_user(
            'sbs_task_empty_write_probe',
            self.env.ref('sbs_project_extension.group_sbs_task_read_create'),
        )
        empty_tasks = self.env['project.task'].with_user(read_task_user).browse()

        self.assertTrue(empty_tasks.write({'name': 'No records to change'}))
        self.assertTrue(empty_tasks.unlink())
