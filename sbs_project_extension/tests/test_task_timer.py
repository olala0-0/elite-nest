from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSbsTaskTimer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.timer_model = cls.env['sbs_project_extension.task.timer']
        cls.wizard_model = cls.env['sbs_project_extension.timesheet.log.wizard']
        cls.timesheet_model = cls.env['account.analytic.line']

        cls.project = cls.env['project.project'].create({
            'name': 'SBS Timer Project',
            'allow_timesheets': True,
        })
        cls.task = cls.env['project.task'].create({
            'name': 'SBS Timer Task',
            'project_id': cls.project.id,
        })
        cls.other_task = cls.env['project.task'].create({
            'name': 'SBS Timer Other Task',
            'project_id': cls.project.id,
        })

        cls.user = cls._make_user(
            'sbs_timer_user',
            'sbs_project_extension.group_sbs_project_extension',
        )
        cls.admin_user = cls._make_user(
            'sbs_timer_admin',
            'sbs_project_extension.group_sbs_project_admin',
        )

    @classmethod
    def _make_user(cls, login, group_xml_id):
        user = cls.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': login,
            'login': login,
            'group_ids': [Command.set(cls.env.ref(group_xml_id).ids)],
        })
        cls.env['hr.employee'].create({
            'name': login,
            'user_id': user.id,
            'company_id': cls.env.company.id,
        })
        return user

    def _start(self, task, user):
        return task.with_user(user).action_sbs_timer_start()

    def _timer_of(self, task, user):
        return self.timer_model.sudo().search([
            ('task_id', '=', task.id),
            ('user_id', '=', user.id),
        ], limit=1)

    def test_start_creates_running_timer(self):
        self._start(self.task, self.user)

        timer = self._timer_of(self.task, self.user)
        self.assertTrue(timer)
        self.assertFalse(timer.date_stop)
        self.assertEqual(timer.state, 'running')
        self.assertEqual(
            self.task.with_user(self.user).sbs_timer_state, 'running'
        )

    def test_second_running_timer_is_blocked(self):
        self._start(self.task, self.user)

        with self.assertRaises(UserError):
            self._start(self.other_task, self.user)

        self.assertFalse(self._timer_of(self.other_task, self.user))

    def test_two_users_can_time_the_same_task(self):
        self._start(self.task, self.user)
        self._start(self.task, self.admin_user)

        self.assertTrue(self._timer_of(self.task, self.user))
        self.assertTrue(self._timer_of(self.task, self.admin_user))

    def test_stop_freezes_elapsed_and_opens_wizard(self):
        self._start(self.task, self.user)
        timer = self._timer_of(self.task, self.user)
        timer.write({
            'date_start': fields.Datetime.now() - timedelta(seconds=3725),
        })

        action = self.task.with_user(self.user).action_sbs_timer_stop()

        timer = self._timer_of(self.task, self.user)
        self.assertTrue(timer.date_stop)
        self.assertEqual(timer.state, 'stopped')
        self.assertEqual(
            action['res_model'],
            'sbs_project_extension.timesheet.log.wizard',
        )
        wizard = self.wizard_model.sudo().browse(action['res_id'])
        self.assertAlmostEqual(wizard.measured_hours, 3725 / 3600.0, places=3)
        self.assertAlmostEqual(wizard.hours, wizard.measured_hours, places=6)
        self.assertEqual(
            self.task.with_user(self.user).sbs_timer_state, 'stopped'
        )

    def test_logging_more_than_counted_is_rejected(self):
        wizard = self._stopped_wizard(seconds=3600)

        with self.assertRaises(ValidationError):
            wizard.write({'hours': wizard.measured_hours + 0.5})

    def test_logging_zero_is_rejected(self):
        wizard = self._stopped_wizard(seconds=3600)

        with self.assertRaises(ValidationError):
            wizard.write({'hours': 0.0})

    def test_logging_less_than_counted_creates_timesheet(self):
        wizard = self._stopped_wizard(seconds=3600)
        wizard.write({'hours': 0.25, 'name': 'Partial work'})

        wizard.action_add_to_timesheet()

        line = self.timesheet_model.sudo().search([
            ('task_id', '=', self.task.id),
            ('user_id', '=', self.user.id),
        ])
        self.assertEqual(len(line), 1)
        self.assertAlmostEqual(line.unit_amount, 0.25, places=6)
        self.assertEqual(line.name, 'Partial work')
        self.assertEqual(line.project_id, self.project)
        self.assertFalse(self._timer_of(self.task, self.user))

    def test_discard_timer_removes_it_without_timesheet(self):
        wizard = self._stopped_wizard(seconds=3600)

        wizard.action_discard_timer()

        self.assertFalse(self._timer_of(self.task, self.user))
        self.assertFalse(self.timesheet_model.sudo().search([
            ('task_id', '=', self.task.id),
            ('user_id', '=', self.user.id),
        ]))

    def test_timer_needs_timesheets_enabled_on_project(self):
        self.project.sudo().write({'allow_timesheets': False})

        with self.assertRaises(UserError):
            self._start(self.task, self.user)

    def test_only_project_admin_can_edit_task_timesheet(self):
        wizard = self._stopped_wizard(seconds=3600)
        wizard.action_add_to_timesheet()
        line = self.timesheet_model.sudo().search([
            ('task_id', '=', self.task.id),
            ('user_id', '=', self.user.id),
        ])

        with self.assertRaises(AccessError):
            line.with_user(self.user).write({'unit_amount': 5.0})

        line.with_user(self.admin_user).write({'unit_amount': 5.0})
        self.assertAlmostEqual(line.unit_amount, 5.0, places=6)

    def test_only_project_admin_can_delete_task_timesheet(self):
        wizard = self._stopped_wizard(seconds=3600)
        wizard.action_add_to_timesheet()
        line = self.timesheet_model.sudo().search([
            ('task_id', '=', self.task.id),
            ('user_id', '=', self.user.id),
        ])

        with self.assertRaises(AccessError):
            line.with_user(self.user).unlink()

        line.with_user(self.admin_user).unlink()
        self.assertFalse(line.exists())

    def test_project_timesheet_without_task_is_not_restricted(self):
        line = self.timesheet_model.with_user(self.user).create({
            'name': 'Project level work',
            'project_id': self.project.id,
            'unit_amount': 1.0,
        })
        self.assertFalse(line.task_id)
        self.assertFalse(line._sbs_task_timesheets())

        line.write({'unit_amount': 2.0})

        self.assertAlmostEqual(line.unit_amount, 2.0, places=6)

    def test_user_cannot_tamper_with_their_own_timer(self):
        self._start(self.task, self.user)
        timer = self._timer_of(self.task, self.user)

        with self.assertRaises(AccessError):
            timer.with_user(self.user).write({
                'date_start': fields.Datetime.now() - timedelta(hours=40),
            })

    def test_timer_cannot_stop_before_it_started(self):
        self._start(self.task, self.user)
        timer = self._timer_of(self.task, self.user)

        with self.assertRaises(ValidationError):
            timer.write({
                'date_stop': timer.date_start - timedelta(seconds=1),
            })

    def test_forged_wizard_cannot_inflate_the_timesheet(self):
        wizard = self._stopped_wizard(seconds=60)
        timer = wizard.timer_id

        with self.assertRaises(ValidationError):
            self.wizard_model.with_user(self.user).create({
                'timer_id': timer.id,
                'hours': 999.0,
            })

    def test_logging_is_capped_by_the_timer_at_submit_time(self):
        wizard = self._stopped_wizard(seconds=3600)
        wizard.write({'hours': 0.9})

        timer = self._timer_of(self.task, self.user)
        timer.write({'date_start': timer.date_stop - timedelta(seconds=120)})

        with self.assertRaises(ValidationError):
            wizard.action_add_to_timesheet()

        self.assertFalse(self.timesheet_model.sudo().search([
            ('task_id', '=', self.task.id),
            ('user_id', '=', self.user.id),
        ]))

    def test_logged_task_cannot_be_redirected(self):
        self._start(self.task, self.user)
        timer = self._timer_of(self.task, self.user)
        timer.write({
            'date_start': fields.Datetime.now() - timedelta(seconds=3600),
        })
        self.task.with_user(self.user).action_sbs_timer_stop()
        timer = self._timer_of(self.task, self.user)

        wizard = self.wizard_model.with_user(self.user).create({
            'timer_id': timer.id,
            'task_id': self.other_task.id,
            'hours': 0.25,
        })
        self.assertEqual(wizard.task_id, self.task)

        wizard.action_add_to_timesheet()

        self.assertFalse(self.timesheet_model.sudo().search([
            ('task_id', '=', self.other_task.id),
        ]))
        self.assertEqual(len(self.timesheet_model.sudo().search([
            ('task_id', '=', self.task.id),
        ])), 1)

    def test_task_timesheet_is_flagged_readonly_for_non_admin(self):
        wizard = self._stopped_wizard(seconds=3600)
        wizard.action_add_to_timesheet()
        line = self.timesheet_model.sudo().search([
            ('task_id', '=', self.task.id),
            ('user_id', '=', self.user.id),
        ])

        self.assertTrue(line.with_user(self.user).readonly_timesheet)
        self.assertFalse(line.with_user(self.admin_user).readonly_timesheet)

    def test_core_bookkeeping_fields_are_not_blocked(self):
        wizard = self._stopped_wizard(seconds=3600)
        wizard.action_add_to_timesheet()
        line = self.timesheet_model.sudo().search([
            ('task_id', '=', self.task.id),
            ('user_id', '=', self.user.id),
        ])

        line.with_user(self.user)._check_can_write({'so_line': False})

        with self.assertRaises(AccessError):
            line.with_user(self.user)._check_can_write({'unit_amount': 5.0})

    def test_new_timesheet_row_is_not_flagged_readonly(self):
        draft = self.timesheet_model.with_user(self.user).new({
            'project_id': self.project.id,
            'task_id': self.task.id,
            'unit_amount': 1.0,
        })

        self.assertFalse(draft.readonly_timesheet)

    def test_another_user_cannot_attach_a_wizard_to_your_timer(self):
        wizard = self._stopped_wizard(seconds=3600)
        timer = wizard.timer_id

        with self.assertRaises(ValidationError):
            self.wizard_model.with_user(self.admin_user).create({
                'timer_id': timer.id,
                'hours': 0.1,
            })

    def test_stopping_before_any_time_is_counted_removes_the_timer(self):
        self._start(self.task, self.user)

        action = self.task.with_user(self.user).action_sbs_timer_stop()

        self.assertEqual(action['tag'], 'display_notification')
        self.assertFalse(self._timer_of(self.task, self.user))
        self.assertEqual(
            self.task.with_user(self.user).sbs_timer_state, 'idle'
        )

    def test_logging_works_when_active_company_has_no_employee(self):
        home_company = self.env.company
        other_company = self.env['res.company'].create({'name': 'SBS Timer Co2'})
        user = self.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': 'sbs_timer_mc',
            'login': 'sbs_timer_mc',
            'company_id': other_company.id,
            'company_ids': [Command.set([other_company.id, home_company.id])],
            'group_ids': [Command.set(
                self.env.ref('sbs_project_extension.group_sbs_project_extension').ids
            )],
        })
        self.env['hr.employee'].create({
            'name': 'sbs_timer_mc',
            'user_id': user.id,
            'company_id': home_company.id,
        })
        self.assertFalse(user.with_user(user).employee_id)

        self._start(self.task, user)
        timer = self._timer_of(self.task, user)
        timer.write({
            'date_start': fields.Datetime.now() - timedelta(seconds=3600),
        })
        action = self.task.with_user(user).action_sbs_timer_stop()
        wizard = self.wizard_model.with_user(user).browse(action['res_id'])
        wizard.write({'hours': 0.5})

        wizard.action_add_to_timesheet()

        line = self.timesheet_model.sudo().search([
            ('task_id', '=', self.task.id),
            ('user_id', '=', user.id),
        ])
        self.assertEqual(len(line), 1)
        self.assertAlmostEqual(line.unit_amount, 0.5, places=6)

    def _stopped_wizard(self, seconds):
        self._start(self.task, self.user)
        timer = self._timer_of(self.task, self.user)
        timer.write({
            'date_start': fields.Datetime.now() - timedelta(seconds=seconds),
        })
        action = self.task.with_user(self.user).action_sbs_timer_stop()
        return self.wizard_model.with_user(self.user).browse(action['res_id'])
