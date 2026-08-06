from odoo import api, fields, models


class PropertyInspectionChecklistItem(models.Model):
    _name = 'property.inspection.checklist.item'
    _description = 'Property Inspection Checklist Item'
    _order = 'sequence, id'

    name = fields.Char(string='Item', required=True)
    area = fields.Char(string='Area')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)


class PropertyInspection(models.Model):
    _name = 'property.inspection'
    _description = 'Property Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inspection_date desc, id desc'

    name = fields.Char(string='Reference', default=lambda self: 'New', copy=False, readonly=True)
    rent_contract_id = fields.Many2one(comodel_name='rent.contract', string='Rent Contract', tracking=True)
    property_id = fields.Many2one(comodel_name='property.detail', string='Property', tracking=True)
    tenant_id = fields.Many2one(comodel_name='res.partner', string='Tenant')
    inspection_type = fields.Selection(
        [('move_in', 'Pre-Move-In'), ('move_out', 'Move-Out / Final')],
        string='Type', required=True, default='move_in', tracking=True)
    inspector_id = fields.Many2one(comodel_name='res.users', string='Inspector',
                                   default=lambda self: self.env.user)
    inspection_date = fields.Datetime(string='Inspection Date', default=fields.Datetime.now)
    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    line_ids = fields.One2many(comodel_name='property.inspection.line', inverse_name='inspection_id',
                               string='Checklist')

    state = fields.Selection(
        [('draft', 'Draft'), ('in_progress', 'In Progress'), ('report_shared', 'Report Shared'),
         ('tenant_acknowledged', 'Tenant Acknowledged'), ('done', 'Done')],
        string='Status', default='draft', tracking=True)
    report_shared_date = fields.Datetime(string='Report Shared On', readonly=True)
    tenant_ack_date = fields.Datetime(string='Tenant Acknowledged On', readonly=True)
    tenant_signature = fields.Binary(string='Tenant Signature')

    total_deduction_amount = fields.Monetary(
        string='Total Estimated Deduction', currency_field='currency_id',
        compute='_compute_total_deduction_amount', store=True,
        help="Sum of estimated costs on every checklist line not marked OK. "
             "Feeds the Move-Out deposit settlement once that flow is built.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('property.inspection') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.condition', 'line_ids.estimated_cost')
    def _compute_total_deduction_amount(self):
        for rec in self:
            rec.total_deduction_amount = sum(
                rec.line_ids.filtered(lambda line: line.condition != 'ok').mapped('estimated_cost')
            )

    @api.onchange('rent_contract_id')
    def _onchange_rent_contract_id(self):
        """Convenience prefill only - matches the same pattern already used
        on account.move (_onchange_partner_id_set_contract_property). Does
        not write back to the contract."""
        if self.rent_contract_id:
            if self.rent_contract_id.property_id:
                self.property_id = self.rent_contract_id.property_id
            if self.rent_contract_id.tenant_id:
                self.tenant_id = self.rent_contract_id.tenant_id

    @api.onchange('inspection_type')
    def _onchange_inspection_type_load_checklist(self):
        """Pre-fill the checklist from the master list the first time a type
        is picked on a brand-new inspection, so inspectors aren't starting
        from a blank list every time. Only fires while the line list is
        still empty, so it never overwrites work already in progress."""
        if self.inspection_type and not self.line_ids:
            items = self.env['property.inspection.checklist.item'].search([])
            self.line_ids = [
                (0, 0, {'checklist_item_id': item.id, 'name': item.name})
                for item in items
            ]

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'

    def action_share_report(self):
        for rec in self:
            rec.write({'state': 'report_shared', 'report_shared_date': fields.Datetime.now()})

    def action_tenant_acknowledge(self):
        for rec in self:
            rec.write({'state': 'tenant_acknowledged', 'tenant_ack_date': fields.Datetime.now()})

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'


class PropertyInspectionLine(models.Model):
    _name = 'property.inspection.line'
    _description = 'Property Inspection Checklist Line'
    _order = 'sequence, id'

    inspection_id = fields.Many2one(comodel_name='property.inspection', string='Inspection',
                                    required=True, ondelete='cascade')
    checklist_item_id = fields.Many2one(comodel_name='property.inspection.checklist.item',
                                        string='Checklist Item')
    sequence = fields.Integer(string='Sequence', default=10)
    area = fields.Char(string='Area')
    name = fields.Char(string='Item', required=True)
    condition = fields.Selection(
        [('ok', 'OK'), ('damaged', 'Damaged'), ('missing', 'Missing')],
        string='Condition', default='ok', required=True)
    notes = fields.Char(string='Notes')
    photo = fields.Binary(string='Photo')
    estimated_cost = fields.Monetary(string='Estimated Cost', currency_field='currency_id')
    currency_id = fields.Many2one(related='inspection_id.currency_id', string='Currency',
                                  store=True, readonly=True)

    @api.onchange('checklist_item_id')
    def _onchange_checklist_item_id(self):
        if self.checklist_item_id:
            self.name = self.checklist_item_id.name
            self.area = self.checklist_item_id.area
            self.sequence = self.checklist_item_id.sequence
