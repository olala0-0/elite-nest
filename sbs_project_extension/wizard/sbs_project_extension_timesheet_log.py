from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


HOURS_PRECISION = 6


class SbsProjectExtensionTimesheetLog(models.TransientModel):
    _name = 'sbs_project_extension.timesheet.log.wizard'
    _description = 'Log Counted Time to Timesheet'

    timer_id = fields.Many2one(
        'sbs_project_extension.task.timer',
        string="Timer",
        required=True,
        ondelete='cascade',
    )
    task_id = fields.Many2one(
        related='timer_id.task_id',
        string="Task",
        readonly=True,
    )
    project_id = fields.Many2one(
        related='task_id.project_id',
        string="Project",
        readonly=True,
    )
    measured_hours = fields.Float(
        string="Counted Time",
        compute='_compute_measured_hours',
        digits=(16, 6),
    )
    hours = fields.Float(
        string="Time to Log",
        required=True,
        digits=(16, 6),
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )
    name = fields.Char(string="Description")

    @api.depends('timer_id.date_start', 'timer_id.date_stop')
    def _compute_measured_hours(self):
        for wizard in self:
            wizard.measured_hours = wizard.timer_id.sudo().elapsed_hours

    @api.constrains('timer_id')
    def _check_timer_is_own(self):
        for wizard in self:
            timer = wizard.timer_id.sudo()
            if (
                timer
                and wizard.env.uid != SUPERUSER_ID
                and timer.user_id.id != wizard.env.uid
            ):
                raise ValidationError(_(
                    "You can only log your own counted time."
                ))

    @api.constrains('hours', 'timer_id')
    def _check_hours_not_increased(self):
        for wizard in self:
            wizard._assert_hours_within_counted(wizard.measured_hours)

    def _assert_hours_within_counted(self, counted):
        self.ensure_one()
        if float_compare(
            self.hours, 0.0, precision_digits=HOURS_PRECISION
        ) <= 0:
            raise ValidationError(_(
                "The time to log must be greater than zero."
            ))
        if float_compare(
            self.hours, counted, precision_digits=HOURS_PRECISION
        ) > 0:
            raise ValidationError(_(
                "You can only reduce the counted time. The timer counted "
                "%(counted)s hours, so you cannot log %(asked)s hours.",
                counted=counted,
                asked=self.hours,
            ))

    def action_add_to_timesheet(self):
        self.ensure_one()
        timer = self.timer_id.sudo()
        if not timer.exists():
            raise UserError(_(
                "This timer no longer exists. Start the timer again to count "
                "new time."
            ))
        if timer.user_id != self.env.user and not self.env.su:
            raise UserError(_("You can only log your own counted time."))
        task = self.env['project.task'].browse(timer.task_id.id)
        task._sbs_check_timesheet_allowed()
        has_employee = self.env['hr.employee'].sudo().search_count(
            [('user_id', '=', self.env.uid)], limit=1
        )
        if not has_employee:
            raise UserError(_(
                "Your user is not linked to an employee, so timesheets cannot "
                "be created. Ask an administrator to link an employee to your "
                "user."
            ))
        self._assert_hours_within_counted(timer.elapsed_hours)
        self.env['account.analytic.line'].create({
            'name': self.name or '/',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'date': self.date,
            'unit_amount': self.hours,
        })
        timer.unlink()
        return {'type': 'ir.actions.act_window_close'}

    def action_discard_timer(self):
        self.ensure_one()
        timer = self.timer_id.sudo()
        if timer.exists():
            if timer.user_id != self.env.user and not self.env.su:
                raise UserError(_("You can only discard your own timer."))
            timer.unlink()
        return {'type': 'ir.actions.act_window_close'}
