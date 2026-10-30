from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL


PROJECT_GENERAL_GROUP = (
    'sbs_project_extension.group_sbs_project_extension'
)
PROJECT_PASSWORD_GROUP = (
    'sbs_project_extension.group_sbs_project_password_user'
)
PROJECT_FINANCIAL_GROUP = (
    'sbs_project_extension.group_sbs_project_financial_user'
)
PROJECT_ADMIN_GROUP = 'sbs_project_extension.group_sbs_project_admin'
PROJECT_TASK_READ_CREATE_GROUP = (
    'sbs_project_extension.group_sbs_task_read_create'
)
PROJECT_LOCK_ADMIN_GROUP = 'base.group_system'
PROJECT_ROLE_PRIVILEGE = (
    'sbs_project_extension.privilege_sbs_project_role'
)

TEAM_FIELD_NAMES = (
    'sp_ids',
    'pm_ids',
    'developer_ids',
    'qa_ids',
    'fa_ids',
    'pc_ids',
    'kam_ids',
    'csm_ids',
)
CREDENTIAL_FIELD_NAMES = (
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
FINANCIAL_FIELD_NAMES = (
    'proposed_value',
    'locked_value',
    'revised_value',
)
SBS_DETAIL_SETUP_TOKEN = object()


class SbsProjectLinkedMixin(models.AbstractModel):
    _name = 'sbs.project.linked.mixin'
    _description = 'Project-linked Record Access'

    @api.model
    def _search(
        self,
        domain,
        offset=0,
        limit=None,
        order=None,
        *,
        active_test=True,
        bypass_access=False,
    ):
        if not self.env.su and not bypass_access:
            Project = self.env['project.project'].with_context(
                active_test=False
            )
            domain = Domain(domain) & Domain(
                'project_id',
                'in',
                Project._search(Domain.TRUE, active_test=False),
            )
        return super()._search(
            domain,
            offset,
            limit,
            order,
            active_test=active_test,
            bypass_access=bypass_access,
        )

    def _check_access(self, operation):
        result = super()._check_access(operation)
        if self.env.su or not self:
            return result

        records = self - result[0] if result else self
        projects = records.sudo().project_id.with_user(self.env.user)
        accessible_project_ids = set(projects._filtered_access('read').ids)
        forbidden = records.filtered(
            lambda record: record.sudo().project_id.id
            not in accessible_project_ids
        )
        if forbidden:
            if result:
                forbidden |= result[0]
                error = result[1]
            else:
                message = _(
                    "You cannot access this project detail because you cannot "
                    "read its project."
                )
                error = lambda: AccessError(message)
            return forbidden, error
        return result

    @api.model_create_multi
    def create(self, vals_list):
        project_ids = {
            vals.get('project_id')
            for vals in vals_list
            if vals.get('project_id')
        }
        if project_ids:
            projects = self.env['project.project'].browse(project_ids)
            projects.check_access('read')
            if (
                self.env.context.get('_sbs_detail_setup_token')
                is not SBS_DETAIL_SETUP_TOKEN
            ):
                projects._sbs_check_unlocked()
        return super().create(vals_list)

    def write(self, vals):
        projects = self.sudo().project_id
        if vals.get('project_id'):
            new_project = self.env['project.project'].browse(
                vals['project_id']
            )
            new_project.check_access('read')
            projects |= new_project.sudo()
        if (
            self.env.context.get('_sbs_detail_setup_token')
            is not SBS_DETAIL_SETUP_TOKEN
        ):
            projects._sbs_check_unlocked()
        return super().write(vals)

    def unlink(self):
        if (
            self.env.context.get('_sbs_detail_setup_token')
            is not SBS_DETAIL_SETUP_TOKEN
        ):
            self.sudo().project_id._sbs_check_unlocked()
        return super().unlink()

class ProjectProject(models.Model):
    _inherit = 'project.project'
    _order = 'sbs_priority_number, sequence, name, id'

    sbs_is_locked = fields.Boolean(
        string="Locked",
        copy=False,
        readonly=True,
        tracking=True,
    )
    sbs_priority_number = fields.Integer(
        string="Priority Number",
        default=0,
        index=True,
        tracking=True,
        help="Lower positive numbers are shown first; zero is shown last.",
    )
    sbs_project_director = fields.Many2one(
        'res.users',
        string="Project Director",
        tracking=True,
        domain=[('share', '=', False)],
    )
    risk_level = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        string="Risk Level",
        groups=PROJECT_GENERAL_GROUP,
    )
    delivery_type = fields.Selection(
        [
            ('amc', 'AMC'),
            ('development', 'Development'),
            ('pending', 'Payment Pending'),
        ],
        string="Delivery Type",
        groups=PROJECT_GENERAL_GROUP,
    )
    next_action = fields.Char(
        "Next Action", groups=PROJECT_GENERAL_GROUP
    )
    risk_factor_id = fields.Many2one(
        'sbs_project_extension.risk.factor',
        string="Risk Factor",
        groups=PROJECT_GENERAL_GROUP,
    )
    industry_id = fields.Many2one(
        'sbs_project_extension.industry',
        string="Industry",
        groups=PROJECT_GENERAL_GROUP,
    )
    tech_stack_id = fields.Many2one(
        'sbs_project_extension.tech.stack',
        string="Tech Stack",
        groups=PROJECT_GENERAL_GROUP,
    )
    review_line_ids = fields.One2many(
        'sbs_project_extension.review.line',
        'project_id',
        string="Review History",
        readonly=True,
        groups=PROJECT_GENERAL_GROUP,
    )
    team_formation_type = fields.Selection(
        [('internal', 'Internal'), ('hybrid', 'Hybrid')],
        string="Team Formation Type",
        default='hybrid',
        required=True,
        groups=PROJECT_GENERAL_GROUP,
    )
    fa_ids = fields.Many2many(
        'sbs_project_extension.project.team',
        'project_team_fa_rel',
        string="Functional Consultants",
        groups=PROJECT_GENERAL_GROUP,
    )
    developer_ids = fields.Many2many(
        'sbs_project_extension.project.team',
        'project_team_dev_rel',
        string="Developers",
        groups=PROJECT_GENERAL_GROUP,
    )
    qa_ids = fields.Many2many(
        'sbs_project_extension.project.team',
        'project_team_qa_rel',
        string="QAs",
        groups=PROJECT_GENERAL_GROUP,
    )
    sp_ids = fields.Many2many(
        'sbs_project_extension.project.team',
        'project_team_sp_rel',
        string="Sales Persons",
        groups=PROJECT_GENERAL_GROUP,
    )
    pm_ids = fields.Many2many(
        'sbs_project_extension.project.team',
        'project_team_pm_rel',
        string="Project Managers",
        groups=PROJECT_GENERAL_GROUP,
    )
    pc_ids = fields.Many2many(
        'sbs_project_extension.project.team',
        'project_team_pc_rel',
        string="Project Coordinators",
        groups=PROJECT_GENERAL_GROUP,
    )
    kam_ids = fields.Many2many(
        'sbs_project_extension.project.team',
        'project_team_kam_rel',
        string="Key Account Managers",
        groups=PROJECT_GENERAL_GROUP,
    )
    csm_ids = fields.Many2many(
        'sbs_project_extension.project.team',
        'project_team_csm_rel',
        string="Client Success Managers",
        groups=PROJECT_GENERAL_GROUP,
    )
    sbs_lead_developer_id = fields.Many2one(
        'sbs_project_extension.project.team',
        string="Lead Developer",
        compute='_compute_sbs_lead_members',
        store=True,
        readonly=False,
        domain="[('id', 'in', developer_ids)]",
        groups=PROJECT_GENERAL_GROUP,
        help="Team member whose photo represents development on the Kanban "
             "card. Defaults to the first developer and can be changed.",
    )
    sbs_lead_fa_id = fields.Many2one(
        'sbs_project_extension.project.team',
        string="Lead Functional Consultant",
        compute='_compute_sbs_lead_members',
        store=True,
        readonly=False,
        domain="[('id', 'in', fa_ids)]",
        groups=PROJECT_GENERAL_GROUP,
        help="Team member whose photo represents functional consulting on "
             "the Kanban card. Defaults to the first consultant and can be "
             "changed.",
    )
    sbs_lead_developer_user_id = fields.Many2one(
        'res.users',
        string="Lead Developer User",
        compute='_compute_sbs_lead_team_user_ids',
        groups=PROJECT_GENERAL_GROUP,
    )
    sbs_lead_fa_user_id = fields.Many2one(
        'res.users',
        string="Lead Functional Consultant User",
        compute='_compute_sbs_lead_team_user_ids',
        groups=PROJECT_GENERAL_GROUP,
    )

    git_repo_link = fields.Char(
        "Git Repo Link", groups=PROJECT_GENERAL_GROUP
    )
    git_repo_creator = fields.Char(
        "Git Repo Creator", groups=PROJECT_GENERAL_GROUP
    )
    git_repo_privacy = fields.Selection(
        [('public', 'Public'), ('private', 'Private')],
        string="Git Privacy",
        groups=PROJECT_GENERAL_GROUP,
    )
    whatsapp_group = fields.Char(
        "WhatsApp Group Name", groups=PROJECT_GENERAL_GROUP
    )
    cloud_storage = fields.Char(
        "Cloud Storage Link", groups=PROJECT_GENERAL_GROUP
    )

    client_name = fields.Char(
        "Client Name", groups=PROJECT_GENERAL_GROUP
    )
    client_address = fields.Text(
        "Client Address", groups=PROJECT_GENERAL_GROUP
    )
    client_country_id = fields.Many2one(
        'res.country',
        string="Client Country",
        groups=PROJECT_GENERAL_GROUP,
    )
    client_website = fields.Char(
        "Client Website", groups=PROJECT_GENERAL_GROUP
    )
    spoc_name = fields.Char("SPOC Name", groups=PROJECT_GENERAL_GROUP)
    spoc_designation = fields.Char(
        "SPOC Designation", groups=PROJECT_GENERAL_GROUP
    )
    spoc_phone = fields.Char("SPOC Phone", groups=PROJECT_GENERAL_GROUP)
    spoc_email = fields.Char("SPOC Email", groups=PROJECT_GENERAL_GROUP)
    spoc_cc_email = fields.Char("CC Email", groups=PROJECT_GENERAL_GROUP)

    credential_detail_ids = fields.One2many(
        'sbs_project_extension.project.credentials',
        'project_id',
        string="Credential Details",
        groups=PROJECT_PASSWORD_GROUP,
    )
    credential_detail_id = fields.Many2one(
        'sbs_project_extension.project.credentials',
        compute='_compute_sbs_detail_ids',
        compute_sudo=True,
        search='_search_credential_detail_id',
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_hosting = fields.Char(
        related='credential_detail_id.prod_hosting',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_link = fields.Char(
        related='credential_detail_id.prod_link',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_db = fields.Char(
        related='credential_detail_id.prod_db',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_user = fields.Char(
        related='credential_detail_id.prod_user',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_pass = fields.Char(
        related='credential_detail_id.prod_pass',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_master_pass = fields.Char(
        related='credential_detail_id.prod_master_pass',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_server_ip = fields.Char(
        related='credential_detail_id.prod_server_ip',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_server_user = fields.Char(
        related='credential_detail_id.prod_server_user',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_server_password = fields.Char(
        related='credential_detail_id.prod_server_password',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    prod_server_os = fields.Char(
        related='credential_detail_id.prod_server_os',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )

    stag_hosting = fields.Char(
        related='credential_detail_id.stag_hosting',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    stag_link = fields.Char(
        related='credential_detail_id.stag_link',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    stag_db = fields.Char(
        related='credential_detail_id.stag_db',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    stag_user = fields.Char(
        related='credential_detail_id.stag_user',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    stag_pass = fields.Char(
        related='credential_detail_id.stag_pass',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    stag_master_pass = fields.Char(
        related='credential_detail_id.stag_master_pass',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    stag_server_ip = fields.Char(
        related='credential_detail_id.stag_server_ip',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    stag_server_user = fields.Char(
        related='credential_detail_id.stag_server_user',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    stag_server_password = fields.Char(
        related='credential_detail_id.stag_server_password',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )
    stag_server_os = fields.Char(
        related='credential_detail_id.stag_server_os',
        readonly=False,
        groups=PROJECT_PASSWORD_GROUP,
    )

    amc_status = fields.Selection(
        [
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('development', 'Development'),
            ('inactive', 'Inactive'),
        ],
        string="AMC Status",
        groups=PROJECT_GENERAL_GROUP,
    )
    free_amc_start_date = fields.Date(
        "Free AMC Start Date", groups=PROJECT_GENERAL_GROUP
    )
    free_amc_expiry_date = fields.Date(
        "Free AMC Expiry Date", groups=PROJECT_GENERAL_GROUP
    )
    amc_start_date = fields.Date(
        "AMC Start Date", groups=PROJECT_GENERAL_GROUP
    )
    amc_expiry_date = fields.Date(
        "AMC Expiry Date", groups=PROJECT_GENERAL_GROUP
    )
    amc_remarks = fields.Char("Remarks", groups=PROJECT_GENERAL_GROUP)

    additional_notes = fields.Html(
        "Additional Notes", groups=PROJECT_GENERAL_GROUP
    )

    financial_detail_ids = fields.One2many(
        'sbs_project_extension.project.financial',
        'project_id',
        string="Financial Details",
        groups=PROJECT_FINANCIAL_GROUP,
    )
    financial_detail_id = fields.Many2one(
        'sbs_project_extension.project.financial',
        compute='_compute_sbs_detail_ids',
        compute_sudo=True,
        search='_search_financial_detail_id',
        groups=PROJECT_FINANCIAL_GROUP,
    )
    proposed_value = fields.Monetary(
        related='financial_detail_id.proposed_value',
        readonly=False,
        currency_field='currency_id',
        groups=PROJECT_FINANCIAL_GROUP,
    )
    locked_value = fields.Monetary(
        related='financial_detail_id.locked_value',
        readonly=False,
        currency_field='currency_id',
        groups=PROJECT_FINANCIAL_GROUP,
    )
    revised_value = fields.Monetary(
        related='financial_detail_id.revised_value',
        readonly=False,
        currency_field='currency_id',
        groups=PROJECT_FINANCIAL_GROUP,
    )

    collection_plan_ids = fields.One2many(
        'sbs_project_extension.collection.plan',
        'project_id',
        string="Collection Plan",
        groups=PROJECT_FINANCIAL_GROUP,
    )
    collection_history_ids = fields.One2many(
        'sbs_project_extension.collection.history',
        'project_id',
        string="Collection History",
        groups=PROJECT_FINANCIAL_GROUP,
    )

    @api.depends('credential_detail_ids', 'financial_detail_ids')
    def _compute_sbs_detail_ids(self):
        for project in self:
            project.credential_detail_id = (
                project.credential_detail_ids[:1]
            )
            project.financial_detail_id = project.financial_detail_ids[:1]

    @api.depends('developer_ids', 'fa_ids')
    def _compute_sbs_lead_members(self):
        for project in self:
            if project.sbs_lead_developer_id not in project.developer_ids:
                project.sbs_lead_developer_id = project.developer_ids[:1]
            if project.sbs_lead_fa_id not in project.fa_ids:
                project.sbs_lead_fa_id = project.fa_ids[:1]

    @api.depends('sbs_lead_developer_id.user_id', 'sbs_lead_fa_id.user_id')
    def _compute_sbs_lead_team_user_ids(self):
        for project in self:
            project.sbs_lead_developer_user_id = (
                project.sbs_lead_developer_id.user_id
            )
            project.sbs_lead_fa_user_id = project.sbs_lead_fa_id.user_id

    @api.model
    def _search_credential_detail_id(self, operator, value):
        return Domain('credential_detail_ids', operator, value)

    @api.model
    def _search_financial_detail_id(self, operator, value):
        return Domain('financial_detail_ids', operator, value)

    @api.model
    def _sbs_get_detail_model(self, model_name):
        if model_name not in (
            'sbs_project_extension.project.credentials',
            'sbs_project_extension.project.financial',
        ):
            raise ValueError(f"Unsupported SBS detail model: {model_name}")
        return self.env[model_name].sudo().with_context(
            _sbs_detail_setup_token=SBS_DETAIL_SETUP_TOKEN
        )

    def _sbs_ensure_detail_records(self):
        projects = self.sudo().exists()
        if not projects:
            return

        for model_name in (
            'sbs_project_extension.project.credentials',
            'sbs_project_extension.project.financial',
        ):
            Detail = self._sbs_get_detail_model(model_name)
            existing_project_ids = set(
                Detail.search([
                    ('project_id', 'in', projects.ids),
                ]).project_id.ids
            )
            missing_projects = projects.filtered(
                lambda project: project.id not in existing_project_ids
            )
            if missing_projects:
                Detail.create([
                    {'project_id': project.id}
                    for project in missing_projects
                ])

    def _sbs_check_project_admin(self, operation):
        if self.env.su or self.env.user.has_group(PROJECT_ADMIN_GROUP):
            return
        raise AccessError(_(
            "Only an SBS Project Admin can %(operation)s a project.",
            operation=operation,
        ))

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            and not self.env.user.has_group(PROJECT_ADMIN_GROUP)
        ):
            self._sbs_check_project_admin(_("create"))

        clean_vals_list = []
        detail_values = []
        for values in vals_list:
            values = dict(values)
            credential_values = {
                field_name: values.pop(field_name)
                for field_name in CREDENTIAL_FIELD_NAMES
                if field_name in values
            }
            financial_values = {
                field_name: values.pop(field_name)
                for field_name in FINANCIAL_FIELD_NAMES
                if field_name in values
            }
            clean_vals_list.append(values)
            detail_values.append((credential_values, financial_values))

        projects = super().create(clean_vals_list)
        projects._sbs_ensure_detail_records()
        Credentials = self._sbs_get_detail_model(
            'sbs_project_extension.project.credentials'
        )
        Financials = self._sbs_get_detail_model(
            'sbs_project_extension.project.financial'
        )
        for project, (credential_values, financial_values) in zip(
            projects, detail_values
        ):
            if credential_values:
                Credentials.search([
                    ('project_id', '=', project.id),
                ], limit=1).write(credential_values)
            if financial_values:
                Financials.search([
                    ('project_id', '=', project.id),
                ], limit=1).write(financial_values)
        return projects

    @api.constrains('sbs_priority_number')
    def _check_sbs_priority_number(self):
        if any(project.sbs_priority_number < 0 for project in self):
            raise ValidationError(_(
                "The project priority number cannot be negative."
            ))

    @api.constrains('team_formation_type', *TEAM_FIELD_NAMES)
    def _check_internal_team_members(self):
        Team = self.env['sbs_project_extension.project.team']
        for project in self.filtered(
            lambda record: record.team_formation_type == 'internal'
        ):
            members = Team
            for field_name in TEAM_FIELD_NAMES:
                members |= project[field_name]
            external_members = members.filtered(lambda member: not member.user_id)
            if external_members:
                raise ValidationError(_(
                    "Remove external team members before changing %(project)s "
                    "to an Internal team: %(members)s",
                    project=project.display_name,
                    members=', '.join(external_members.mapped('display_name')),
                ))

    def _order_field_to_sql(
        self, alias, field_name, direction, nulls, query
    ):
        if field_name == 'sbs_priority_number':
            sql_field = self._field_to_sql(alias, field_name, query)
            query._order_groupby.append(sql_field)
            return SQL(
                "NULLIF(%s, 0) %s NULLS LAST",
                sql_field,
                direction if direction.code else SQL("ASC"),
            )
        return super()._order_field_to_sql(
            alias, field_name, direction, nulls, query
        )

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if (
            not self.env.su
            and not self.env.user.has_group(PROJECT_ADMIN_GROUP)
        ):
            arch.set('create', 'false')
            arch.set('delete', 'false')
        if view_type != 'form':
            return arch, view

        project_field_nodes = [
            node
            for node in arch.iter('field')
            if not any(
                ancestor.tag in ('button', 'field')
                for ancestor in node.iterancestors()
            )
        ]
        if not any(
            node.get('name') == 'sbs_is_locked'
            for node in project_field_nodes
        ):
            lock_field = etree.Element(
                'field',
                name='sbs_is_locked',
                invisible='True',
                readonly='True',
            )
            arch.append(lock_field)
            project_field_nodes.append(lock_field)

        for node in project_field_nodes:
            if node.get('name') == 'sbs_is_locked':
                continue
            readonly = node.get('readonly')
            if readonly in ('1', 'True'):
                continue
            if not readonly or readonly in ('0', 'False'):
                node.set('readonly', 'sbs_is_locked')
            else:
                node.set(
                    'readonly',
                    f"({readonly}) or sbs_is_locked",
                )
        return arch, view

    def _sbs_check_lock_admin(self):
        if not self.env.user.has_group(PROJECT_LOCK_ADMIN_GROUP):
            raise AccessError(
                _("Only a Super Admin can lock or unlock projects.")
            )

    def _sbs_check_unlocked(self):
        locked_projects = self.sudo().filtered('sbs_is_locked')
        if locked_projects:
            raise UserError(_(
                "Unlock the following projects before modifying them: "
                "%(projects)s",
                projects=', '.join(
                    locked_projects.mapped('display_name')
                ),
            ))

    def action_sbs_lock(self):
        self.ensure_one()
        self._sbs_check_lock_admin()
        if not self.sbs_is_locked:
            super(ProjectProject, self).write({
                'sbs_is_locked': True,
            })
        return True

    def action_sbs_unlock(self):
        self.ensure_one()
        self._sbs_check_lock_admin()
        if self.sbs_is_locked:
            super(ProjectProject, self).write({
                'sbs_is_locked': False,
            })
        return True

    def write(self, vals):
        if 'sbs_is_locked' in vals:
            raise AccessError(_(
                "Use the Lock or Unlock button to change a project's lock "
                "status."
            ))
        self._sbs_check_unlocked()
        return super().write(vals)

    def unlink(self):
        self._sbs_check_project_admin(_("delete"))
        self._sbs_check_unlocked()
        return super().unlink()

class SbsProjectExtensionRiskFactor(models.Model):
    _name = 'sbs_project_extension.risk.factor'
    _description = 'Risk Factor'
    name = fields.Char(required=True)

class SbsProjectExtensionProjectTeam(models.Model):
    _name = 'sbs_project_extension.project.team'
    _description = 'Project Team'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users',
        string="Internal User",
        index=True,
        ondelete='set null',
        domain=[('share', '=', False)],
    )

    _unique_user = models.Constraint(
        'UNIQUE(user_id)',
        'An internal user can have only one project team entry.',
    )

    @api.model
    def _sbs_internal_user_name(self, user):
        return (
            user.display_name
            or user.login
            or _("Internal User %(user_id)s", user_id=user.id)
        )

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            and any(vals.get('user_id') for vals in vals_list)
        ):
            raise AccessError(_(
                "Internal project team entries are synchronized from users."
            ))
        for vals in vals_list:
            if vals.get('user_id') and not vals.get('name'):
                user = self.env['res.users'].browse(vals['user_id'])
                vals['name'] = self._sbs_internal_user_name(user)
        return super().create(vals_list)

    def write(self, vals):
        if (
            not self.env.su
            and self.filtered('user_id')
            and {'name', 'active', 'user_id'} & vals.keys()
        ):
            raise AccessError(_(
                "Internal project team entries are synchronized from users."
            ))
        return super().write(vals)

    def unlink(self):
        if not self.env.su and self.filtered('user_id'):
            raise AccessError(_(
                "Internal project team entries cannot be deleted."
            ))
        return super().unlink()

class SbsProjectExtensionIndustry(models.Model):
    _name = 'sbs_project_extension.industry'
    _description = 'Industry'
    name = fields.Char(required=True)

class SbsProjectExtensionTechStack(models.Model):
    _name = 'sbs_project_extension.tech.stack'
    _description = 'Tech Stack'
    name = fields.Char(required=True)


class SbsProjectExtensionProjectCredentials(models.Model):
    _name = 'sbs_project_extension.project.credentials'
    _inherit = 'sbs.project.linked.mixin'
    _description = 'Project Credentials'
    _rec_name = 'project_id'
    _order = 'project_id'

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        required=True,
        index=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='project_id.company_id', store=True, readonly=True
    )

    prod_hosting = fields.Char("Production Hosting")
    prod_link = fields.Char("Production Link")
    prod_db = fields.Char("Production DB")
    prod_user = fields.Char("Production User")
    prod_pass = fields.Char("Production Password")
    prod_master_pass = fields.Char("Production Master Password")
    prod_server_ip = fields.Char("Production Server IP")
    prod_server_user = fields.Char("Production SSH User")
    prod_server_password = fields.Char("Production SSH Password")
    prod_server_os = fields.Char("Production OS")

    stag_hosting = fields.Char("Staging Hosting")
    stag_link = fields.Char("Staging Link")
    stag_db = fields.Char("Staging DB")
    stag_user = fields.Char("Staging User")
    stag_pass = fields.Char("Staging Password")
    stag_master_pass = fields.Char("Staging Master Password")
    stag_server_ip = fields.Char("Staging Server IP")
    stag_server_user = fields.Char("Staging Server SSH User")
    stag_server_password = fields.Char("Staging SSH Password")
    stag_server_os = fields.Char("Staging OS")

    _unique_project = models.Constraint(
        'UNIQUE(project_id)',
        'A project can have only one credential record.',
    )


class SbsProjectExtensionProjectFinancial(models.Model):
    _name = 'sbs_project_extension.project.financial'
    _inherit = 'sbs.project.linked.mixin'
    _description = 'Project Financial Details'
    _rec_name = 'project_id'
    _order = 'project_id'

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        required=True,
        index=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='project_id.company_id', store=True, readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_currency_id',
        string="Currency",
        readonly=True,
    )
    proposed_value = fields.Monetary(
        string="Proposed Value", currency_field='currency_id'
    )
    locked_value = fields.Monetary(
        string="Locked Value", currency_field='currency_id'
    )
    revised_value = fields.Monetary(
        string="Revised Value", currency_field='currency_id'
    )

    _unique_project = models.Constraint(
        'UNIQUE(project_id)',
        'A project can have only one financial record.',
    )

    @api.depends_context('company')
    @api.depends('project_id.company_id')
    def _compute_currency_id(self):
        for detail in self:
            detail.currency_id = detail.project_id.currency_id


class SbsProjectExtensionCollectionPlan(models.Model):
    _name = 'sbs_project_extension.collection.plan'
    _inherit = 'sbs.project.linked.mixin'
    _description = 'Collection Plan'

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        required=True,
        index=True,
        ondelete='cascade',
    )
    date = fields.Date(string="Date")
    milestone = fields.Char(string="Milestone")
    collection_plan = fields.Char(string="Collection Plan")
    responsible_id = fields.Many2one('res.users', string="Responsible")
    details = fields.Text(string="Details")


class SbsProjectExtensionCollectionHistory(models.Model):
    _name = 'sbs_project_extension.collection.history'
    _inherit = 'sbs.project.linked.mixin'
    _description = 'Collection History'

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        required=True,
        index=True,
        ondelete='cascade',
    )
    currency_id = fields.Many2one(
        related='project_id.currency_id', readonly=True
    )
    date = fields.Date(string="Date")
    milestone = fields.Char(string="Milestone")
    collected_amount = fields.Monetary(
        string="Collected Amount", currency_field='currency_id'
    )
    collected_by_id = fields.Many2one('res.users', string="Collected By")
    details = fields.Text(string="Details")

class SbsProjectExtensionReviewSession(models.Model):
    _name = 'sbs_project_extension.review.session'
    _description = 'Project Review Session'

    name = fields.Char(string='Review Name', required=True)
    date = fields.Date(string='Review Date', default=fields.Date.context_today)

    review_line_ids = fields.One2many('sbs_project_extension.review.line', 'review_id', string='Review Lines', copy=True,
    )

    @api.model
    def _search(
        self,
        domain,
        offset=0,
        limit=None,
        order=None,
        *,
        active_test=True,
        bypass_access=False,
    ):
        if not self.env.su and not bypass_access:
            Project = self.env['project.project'].with_context(
                active_test=False
            )
            accessible_projects = Project._search(
                Domain.TRUE, active_test=False
            )
            inaccessible_projects = Project.sudo()._search(
                Domain('id', 'not in', accessible_projects),
                active_test=False,
            )
            inaccessible_sessions = self.sudo()._search(Domain(
                'review_line_ids.project_id',
                'in',
                inaccessible_projects,
            ))
            domain = Domain(domain) & Domain(
                'id', 'not in', inaccessible_sessions
            )
        return super()._search(
            domain,
            offset,
            limit,
            order,
            active_test=active_test,
            bypass_access=bypass_access,
        )

    def _check_access(self, operation):
        result = super()._check_access(operation)
        if self.env.su or not self:
            return result

        records = self - result[0] if result else self
        projects = records.sudo().review_line_ids.project_id
        accessible_project_ids = set(
            projects.with_user(self.env.user)._filtered_access('read').ids
        )
        forbidden = records.filtered(
            lambda session: any(
                project.id not in accessible_project_ids
                for project in session.sudo().review_line_ids.project_id
            )
        )
        if forbidden:
            if result:
                forbidden |= result[0]
                error = result[1]
            else:
                message = _(
                    "You cannot access this review session because it "
                    "contains a project you cannot read."
                )
                error = lambda: AccessError(message)
            return forbidden, error
        return result

    def _sbs_check_review_projects_unlocked(self):
        self.sudo().review_line_ids.project_id._sbs_check_unlocked()

    def write(self, vals):
        self.check_access('write')
        self._sbs_check_review_projects_unlocked()
        return super().write(vals)

    def unlink(self):
        self.check_access('unlink')
        self._sbs_check_review_projects_unlocked()
        return super().unlink()

    def copy(self, default=None):
        self.ensure_one()
        self.check_access('read')
        default = dict(default or {})
        review_lines = []
        for line in self.review_line_ids:
            review_lines.append((0, 0, {
                'project_id': line.project_id.id,
                'internal_review': line.internal_review,
                'highlevel_review': line.highlevel_review,
                'internal_datetime': line.internal_datetime,
                'task_frozen': line.task_frozen,
                'completion_percentage': line.completion_percentage,
                'remarks_internal': line.remarks_internal,
                'next_action': line.next_action,
                'customer_review': line.customer_review,
                'customer_datetime': line.customer_datetime,
                'customer_task_frozen': line.customer_task_frozen,
                'customer_completion_percentage': line.customer_completion_percentage,
            }))
        default['review_line_ids'] = review_lines
        return super().copy(default)

class SbsProjectExtensionReviewLine(models.Model):
    _name = 'sbs_project_extension.review.line'
    _inherit = 'sbs.project.linked.mixin'
    _description = 'Project Review Line'

    review_id = fields.Many2one('sbs_project_extension.review.session', string='Review Reference', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', required=True)

    internal_review = fields.Char(string='Review')
    sp_ids = fields.Many2many(related='project_id.sp_ids', string="Sales Person", readonly=True)
    fa_ids = fields.Many2many(related='project_id.fa_ids', string="Functional Consultant", readonly=True)
    pc_ids = fields.Many2many(
        related='project_id.pc_ids',
        string="Project Coordinators",
        readonly=True,
    )
    highlevel_review = fields.Char(string='High-level Review')
    internal_datetime = fields.Datetime(string='Intr. Timeline', default=fields.Datetime.now)
    task_frozen = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Task Frozen")
    completion_percentage = fields.Float(string='% of Completion')
    remarks_internal = fields.Text(string='Remarks')
    next_action = fields.Char(string='Next Action')

    customer_review = fields.Char(string='Customer Review')
    customer_datetime = fields.Datetime(string='Customer Timeline')
    customer_task_frozen = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Customer Task Frozen")
    customer_completion_percentage = fields.Float(string='% of Customer Completion')


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def _sbs_is_project_admin(self):
        return self.env.su or self.env.user.has_group(PROJECT_ADMIN_GROUP)

    def _sbs_is_task_read_create_user(self):
        return (
            not self._sbs_is_project_admin()
            and self.env.user.has_group(PROJECT_TASK_READ_CREATE_GROUP)
        )

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if not self._sbs_is_project_admin():
            arch.set('delete', 'false')
        if self._sbs_is_task_read_create_user():
            arch.set('edit', 'false')
            if view_type == 'kanban':
                arch.set('records_draggable', 'false')
                arch.set('group_create', 'false')
                arch.set('group_edit', 'false')
                arch.set('group_delete', 'false')
        return arch, view

    def write(self, vals):
        if self and self._sbs_is_task_read_create_user():
            raise AccessError(_(
                "Read Task Only users can create tasks but cannot edit them."
            ))
        return super().write(vals)

    def unlink(self):
        if self and not self._sbs_is_project_admin():
            raise AccessError(_(
                "Only an SBS Project Admin can delete tasks."
            ))
        return super().unlink()


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _sbs_sync_project_team_entries(self):
        users = self.sudo().exists()
        if not users:
            return

        Team = self.env[
            'sbs_project_extension.project.team'
        ].sudo().with_context(active_test=False)
        entries = Team.search([('user_id', 'in', users.ids)])
        entries_by_user = {
            entry.user_id.id: entry
            for entry in entries
        }
        to_create = []
        for user in users:
            entry = entries_by_user.get(user.id)
            desired_active = bool(user.active and not user.share)
            desired_name = Team._sbs_internal_user_name(user)
            if entry:
                values = {}
                if entry.name != desired_name:
                    values['name'] = desired_name
                if entry.active != desired_active:
                    values['active'] = desired_active
                if values:
                    entry.write(values)
            elif not user.share:
                to_create.append({
                    'name': desired_name,
                    'user_id': user.id,
                    'active': desired_active,
                })
        if to_create:
            Team.create(to_create)

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sbs_sync_project_team_entries()
        return users

    def write(self, vals):
        result = super().write(vals)
        if {'name', 'active', 'share', 'group_ids'} & vals.keys():
            self._sbs_sync_project_team_entries()
        return result

    @api.constrains('group_ids')
    def _check_sbs_project_role_is_exclusive(self):
        privilege = self.env.ref(
            PROJECT_ROLE_PRIVILEGE,
            raise_if_not_found=False,
        )
        if not privilege:
            return

        role_groups = privilege.group_ids
        for user in self:
            explicit_roles = user.group_ids & role_groups
            if len(explicit_roles) > 1:
                raise ValidationError(_(
                    "A user can have only one SBS Project Role."
                ))
