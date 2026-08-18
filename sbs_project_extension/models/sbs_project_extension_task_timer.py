from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare

from .sbs_project_extension import PROJECT_ADMIN_GROUP


TIMER_MODEL = 'sbs_project_extension.task.timer'
TIMESHEET_LOG_WIZARD = 'sbs_project_extension.timesheet.log.wizard'
HOURS_PRECISION = 6
PROTECTED_TIMESHEET_FIELDS = frozenset({
    'date',
    'employee_id',
    'name',
    'project_id',
    'task_id',
    'unit_amount',
    'user_id',
})


class SbsProjectExtensionTaskTimer(models.Model):
    _name = 'sbs_project_extension.task.timer'
    _description = 'Task Work Timer'
    _rec_name = 'task_id'
    _order = 'date_start desc, id desc'

    task_id = fields.Many2one(
        'project.task',
        string="Task",
        required=True,
        index=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one(
        'res.users',
        string="User",
        required=True,
        index=True,
        default=lambda self: self.env.user,
        ondelete='cascade',
    )
    date_start = fields.Datetime(
        string="Started On",
        required=True,
        default=fields.Datetime.now,
    )
    date_stop = fields.Datetime(string="Stopped On")
    elapsed_hours = fields.Float(
        string="Counted Time",
        compute='_compute_elapsed_hours',
        digits=(16, 6),
    )
    state = fields.Selection(
        [('running', 'Running'), ('stopped', 'Stopped')],
        string="Status",
        compute='_compute_state',
    )

    _task_user_uniq = models.Constraint(
        'UNIQUE(task_id, user_id)',
        "A user can only have one timer per task.",
    )
    _user_running_uniq = models.UniqueIndex(
        "(user_id) WHERE date_stop IS NULL",
        "A user can only have one running timer at a time.",
    )

    @api.depends('date_start', 'date_stop')
    def _compute_elapsed_hours(self):
        now = fields.Datetime.now()
        for timer in self:
            if not timer.date_start:
                timer.elapsed_hours = 0.0
                continue
            end = timer.date_stop or now
            seconds = (end - timer.date_start).total_seconds()
            timer.elapsed_hours = max(0.0, seconds) / 3600.0

    @api.depends('date_stop')
    def _compute_state(self):
        for timer in self:
            timer.state = 'stopped' if timer.date_stop else 'running'

    @api.constrains('date_start', 'date_stop')
    def _check_stop_after_start(self):
        for timer in self:
            if timer.date_stop and timer.date_start > timer.date_stop:
                raise ValidationError(_(
                    "A timer cannot stop before it started."
                ))


class ProjectTaskTimer(models.Model):
    _inherit = 'project.task'

    sbs_timer_state = fields.Selection(
        [
            ('idle', 'No Timer'),
            ('running', 'Running'),
            ('stopped', 'Pending Log'),
        ],
        string="Timer Status",
        compute='_compute_sbs_timer',
    )
    sbs_timer_start = fields.Datetime(
        string="Timer Started On",
        compute='_compute_sbs_timer',
    )
    sbs_timer_elapsed_hours = fields.Float(
        string="Timer Counted Time",
        compute='_compute_sbs_timer',
        digits=(16, 6),
    )

    @api.depends_context('uid')
    def _compute_sbs_timer(self):
        stored = self.filtered(lambda task: isinstance(task.id, int))
        timer_by_task = {}
        if stored:
            timers = self.env[TIMER_MODEL].sudo().search([
                ('task_id', 'in', stored.ids),
                ('user_id', '=', self.env.uid),
            ])
            timer_by_task = {timer.task_id.id: timer for timer in timers}
        for task in self:
            timer = timer_by_task.get(task.id)
            task.sbs_timer_state = timer.state if timer else 'idle'
            task.sbs_timer_start = timer.date_start if timer else False
            task.sbs_timer_elapsed_hours = timer.elapsed_hours if timer else 0.0

    def _sbs_get_user_timer(self):
        self.ensure_one()
        if not isinstance(self.id, int):
            return self.env[TIMER_MODEL].sudo()
        return self.env[TIMER_MODEL].sudo().search([
            ('task_id', '=', self.id),
            ('user_id', '=', self.env.uid),
        ], limit=1)

    def _sbs_check_timesheet_allowed(self):
        for task in self:
            if not task.project_id:
                raise UserError(_(
                    "Time cannot be recorded on a private task. "
                    "Move the task into a project first."
                ))
            if not task.allow_timesheets:
                raise UserError(_(
                    "Timesheets are not enabled on project \"%s\". "
                    "Enable Timesheets on the project first.",
                    task.project_id.display_name,
                ))

    def action_sbs_timer_start(self):
        self.ensure_one()
        self._sbs_check_timesheet_allowed()
        Timer = self.env[TIMER_MODEL].sudo()
        existing = self._sbs_get_user_timer()
        if existing and existing.date_stop:
            raise UserError(_(
                "You already have counted time on this task waiting to be "
                "logged. Use Log Time to add it to the timesheet first."
            ))
        if existing:
            raise UserError(_("A timer is already running on this task."))
        running = Timer.search([
            ('user_id', '=', self.env.uid),
            ('date_stop', '=', False),
        ], limit=1)
        if running:
            raise UserError(_(
                "A timer is already running on task \"%s\". "
                "Stop it before starting a new one.",
                running.task_id.display_name,
            ))
        Timer.create({
            'task_id': self.id,
            'user_id': self.env.uid,
            'date_start': fields.Datetime.now(),
        })
        return True

    def action_sbs_timer_stop(self):
        self.ensure_one()
        timer = self._sbs_get_user_timer()
        if not timer or timer.date_stop:
            raise UserError(_("No timer is running on this task."))
        timer.write({'date_stop': fields.Datetime.now()})
        if float_compare(
            timer.elapsed_hours, 0.0, precision_digits=HOURS_PRECISION
        ) <= 0:
            timer.unlink()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _(
                        "The timer was stopped before any time was counted, "
                        "so nothing was logged."
                    ),
                },
            }
        return self.action_sbs_timer_log()

    def action_sbs_timer_log(self):
        self.ensure_one()
        timer = self._sbs_get_user_timer()
        if not timer:
            raise UserError(_("No timer was found on this task."))
        if not timer.date_stop:
            raise UserError(_(
                "The timer is still running. Stop it before logging the time."
            ))
        wizard = self.env[TIMESHEET_LOG_WIZARD].create({
            'timer_id': timer.id,
            'hours': timer.elapsed_hours,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _("Log Time to Timesheet"),
            'res_model': TIMESHEET_LOG_WIZARD,
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }


class AccountAnalyticLineSbsTimesheet(models.Model):
    _inherit = 'account.analytic.line'

    readonly_timesheet = fields.Boolean(
        compute='_compute_readonly_timesheet',
        compute_sudo=True,
        depends_context=('uid',),
    )

    def _sbs_is_project_admin(self):
        return self.env.su or self.env.user.has_group(PROJECT_ADMIN_GROUP)

    def _sbs_task_timesheets(self):
        return self.sudo().filtered('task_id')

    def _is_readonly(self):
        self.ensure_one()
        if (
            isinstance(self.id, int)
            and self.task_id
            and not self.env.user.has_group(PROJECT_ADMIN_GROUP)
        ):
            return True
        return super()._is_readonly()

    def _check_can_write(self, values):
        if (
            PROTECTED_TIMESHEET_FIELDS.intersection(values)
            and not self._sbs_is_project_admin()
            and self._sbs_task_timesheets()
        ):
            raise AccessError(_(
                "Only an SBS Project Admin can edit task timesheets."
            ))
        return super()._check_can_write(values)

    def unlink(self):
        if not self._sbs_is_project_admin() and self._sbs_task_timesheets():
            raise AccessError(_(
                "Only an SBS Project Admin can delete task timesheets."
            ))
        return super().unlink()
