from odoo import models, fields, api
from datetime import datetime, date


class PropertyProject(models.Model):
    _name = "property.project"
    _description = "Property Project"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Project Name", required=True)
    code = fields.Char(string="Project ID")
    image_1920 = fields.Binary("Image", max_width=1920, max_height=1920)
    is_sub_project = fields.Boolean(string='Sub Project', default=True)

    property_type = fields.Selection(
        [("land", "Land"), ("residential", "Residential"), ("commercial", "Commercial"), ("industrial", "Industrial")],
        string="Property Type", default='land')
    residential_type_id = fields.Many2one(comodel_name="property.residential.type", string="Residential Type")
    residential_type = fields.Char(related="residential_type_id.name", string="Residential Type Text", store=True)

    residential_type = fields.Char(string="Residential Type")
    company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env.company)

    property_for = fields.Selection([("sale", "Sale"), ("rent", "Rent")], string="Property For", default='sale')
    landlord_id = fields.Many2one(comodel_name="res.partner", string="Landlord")

    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street2")
    city = fields.Char(string="City")
    state_id = fields.Many2one(comodel_name="res.country.state", string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one("res.country", string="Country")

    construction_year = fields.Char(string="Construction Year", default=lambda self: str(date.today().year))
    date_of_project = fields.Date(string="Date of Project")
    brochure = fields.Char(string="Brochure")
    website = fields.Char(string="Website")

    latitude = fields.Float(string="Latitude")
    longitude = fields.Float(string="Longitude")

    is_description = fields.Boolean("Description")
    has_amenities = fields.Boolean("Amenities")
    has_specifications = fields.Boolean("Specifications")
    has_images = fields.Boolean("Images")
    has_nearby_connectivities = fields.Boolean("Nearby Connectivities")

    state = fields.Selection([("draft", "Draft"), ("available", "Available"), ("close", "Close")], string="Status",
                             default="draft", tracking=True)

    document_ids = fields.One2many(comodel_name="property.document", inverse_name="project_id", string="Documents")

    valuation_of = fields.Selection([("sale", "Sale"), ("rent", "Rent")], string="Property For", default='sale')

    total_subprojects = fields.Integer(string="Total Sub Project")
    total_property_area = fields.Float(string="Total Property Area")
    available_area = fields.Float(string="Available Area")

    total_value = fields.Monetary(string="Total Value of Project", currency_field="currency_id")
    total_maintenance = fields.Monetary(string="Total Maintenance", currency_field="currency_id")
    total_collection = fields.Monetary(string="Total Collection", currency_field="currency_id")
    scope_collection = fields.Monetary(string="Scope of Collection", currency_field="currency_id")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id.id)
    detail_ids = fields.One2many(comodel_name="property.detail", inverse_name="sub_project_id",
                                 string="Units/Properties")
    description = fields.Text(string="Description")

    specification_ids = fields.One2many(comodel_name="property.specification", inverse_name="project_id",
                                        string="Specifications")
    amenity_ids = fields.One2many(comodel_name="property.amenity", inverse_name="project_id", string="Amenities")

    image_ids = fields.One2many(comodel_name="property.image", inverse_name="project_id", string="Images")

    connectivity_ids = fields.One2many(comodel_name="property.connectivity", inverse_name="project_id",
                                       string="Nearby Connectivities")
    project_manager_id = fields.Many2one(comodel_name="res.users", string="Project Manager",
                                         default=lambda self: self.env.user)
    sub_project_ids = fields.One2many(comodel_name="property.sub.project", inverse_name="project_id",
                                      string="Sub Projects")
    tag_ids = fields.Many2many(comodel_name="property.tag", string="Tags")
    priority = fields.Selection([("0", "Low"), ("1", "Normal"), ("2", "Medium"), ("3", "High")], string="Priority",
                                default="1", index=True)
    internal_ref = fields.Char(string="Internal Reference")
    origin = fields.Char(string="Origin")

    notes = fields.Text(string="Notes")

    document_count = fields.Integer(string="Documents", compute="_compute_document_count")
    sub_project_count = fields.Integer(string="Sub Projects", compute="_compute_sub_project_count")
    property_detail_count = fields.Integer(string="Property", compute="_compute_property_detail_count")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            words = vals.get('name').split()
            vals['code'] = ''.join(word[0].upper() for word in words if word)
        return super().create(vals_list)

    def action_set_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_set_available(self):
        for rec in self:
            rec.state = 'available'

    @api.depends("document_ids")
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    @api.depends("sub_project_ids")
    def _compute_sub_project_count(self):
        for rec in self:
            rec.sub_project_count = len(rec.sub_project_ids)

    def action_open_documents(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Documents",
            "res_model": "property.document",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    def action_open_sub_projects(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Sub Projects",
            "res_model": "property.sub.project",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    @api.depends("detail_ids")
    def _compute_property_detail_count(self):
        for rec in self:
            rec.property_detail_count = len(rec.detail_ids)

    def action_open_property_detail(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Properties",
            "res_model": "property.detail",
            "view_mode": "list,form",
            "domain": [("project_id", "in", self.ids)],
            "context": {"default_project_id": self.id},
        }
