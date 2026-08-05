from odoo import models, fields, api
import uuid
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
import base64


class PropertyDetails(models.Model):
_name = "property.detail"
_description = "Property Detail"
_inherit = ["mail.thread", "mail.activity.mixin"]

name = fields.Char(string="Property Name", required=True)
code = fields.Char(string="Property ID")
access_token = fields.Char(string="Access Token", readonly=True, copy=False)
sub_project_id = fields.Many2one("property.sub.project", string="Sub Project")
project_id = fields.Many2one("property.project", string="Project", related="sub_project_id.project_id",
readonly=False, store=True)

property_type = fields.Selection(
[("land", "Land"), ("residential", "Residential"), ("commercial", "Commercial"), ("industrial", "Industrial")],
string="Property Type", default='land')
residential_type_id = fields.Many2one(comodel_name="property.residential.type", string="Residential Type")
residential_type = fields.Char(related="residential_type_id.name", string="Residential Type Text", store=True)
company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env.company)

property_for = fields.Selection([("sale", "Sale"), ("rent", "Rent")], string="Property For", default='sale')

street = fields.Char(string="Street")
street2 = fields.Char(string="Street2")
city = fields.Char(string="City")
state_id = fields.Many2one(comodel_name="res.country.state", string="State")
zip = fields.Char(string="ZIP")
country_id = fields.Many2one(comodel_name="res.country", string="Country")
latitude = fields.Float(string="Latitude")
longitude = fields.Float(string="Longitude")

landlord_id = fields.Many2one(comodel_name="res.partner", string="Landlord")
phone = fields.Char(string="Phone")
email = fields.Char(string="Email")
website = fields.Char(string="Website")

tag_ids = fields.Many2many(comodel_name="property.tag", string="Tags")
image_1920 = fields.Image("Image", max_width=1920, max_height=1920)

amenities = fields.Boolean("Amenities")
floor_plans = fields.Boolean("Floor Plans")
images = fields.Boolean("Images")
specifications = fields.Boolean("Specifications")
nearby_connectivities = fields.Boolean("Nearby Connectivities")

state = fields.Selection(
[("draft", "Draft"), ("available", "Available"), ("on_rent", "On Rent"), ("on_sale", "On Sale"),
("rent", "Rent"), ("sold", "sold")],
default="draft", string="Status", tracking=True)

total_area = fields.Float(string="Total Area")
usable_area = fields.Float(string="Usable Area")
area_measurement_ids = fields.One2many(comodel_name="property.area.measurement", inverse_name="property_id",
string="Area Measurements")
no_of_floors = fields.Integer(string="No of Floors")
parking = fields.Integer(string="Parking Spaces")
floor = fields.Integer(string="Floor")
facing = fields.Selection(
[('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West'), ('north_east', 'North-East'),
('north_west', 'North-West'), ('south_east', 'South-East'), ('south_west', 'South-West')], string="Facing")
no_of_bhk = fields.Integer(string="BHK")
bedrooms = fields.Integer(string="Bedrooms")
bathrooms = fields.Integer(string="Bathrooms")
furnishing = fields.Selection([('unfurnished', 'Unfurnished'), ('semi_furnished', 'Semi-Furnished'),
('fully_furnished', 'Fully Furnished'), ], string="Furnishing")

pricing_type = fields.Selection([("fixed", "Fixed"), ("area_wise", "Area Wise")], string="Pricing Type",
default="fixed", )
price_per_area = fields.Float(string="Price / Area")
rent_amount = fields.Monetary(string="Rent Amount", currency_field="currency_id")
sale_amount = fields.Monetary(string="Sale Amount", currency_field="currency_id")

is_any_maintenance = fields.Boolean("Is Any Maintenance")
maintenance_type = fields.Selection([("once", "Once"), ("recurring", "Recurring")], string="Maintenance Type",
default='once')
charge_type = fields.Selection([("fixed", "Fixed"), ("area_wise", "Area Wise")], string="Charge Type",
default='fixed')
maintenance = fields.Monetary(string="Maintenance", currency_field="currency_id")
total_maintenance = fields.Monetary(string="Total Maintenance", currency_field="currency_id",
compute="_compute_total_maintenance")

is_utility_services = fields.Boolean(string="Utility Services")
utility_service_ids = fields.One2many(comodel_name="property.utility.service", inverse_name="property_id",
string="Utility Services")

final_price = fields.Monetary(string="Price", currency_field="currency_id", compute="_compute_final_price",
store=True)
total_utility_cost = fields.Monetary(string="Utility Cost", currency_field="currency_id",
compute="_compute_total_utility_cost",
store=True)
total_pricing = fields.Monetary(string="Total", currency_field="currency_id", compute="_compute_total", store=True)
currency_id = fields.Many2one(comodel_name="res.currency", string="Currency",
default=lambda self: self.env.company.currency_id.id)
document_ids = fields.One2many(comodel_name="property.document", inverse_name="property_id", string="Documents")

specification_ids = fields.One2many(comodel_name="property.specification", inverse_name="property_id",
string="Specifications")
amenity_ids = fields.One2many(comodel_name="property.amenity", inverse_name="property_id", string="Amenities")

image_ids = fields.One2many(comodel_name="property.image", inverse_name="property_id", string="Images")

floorplan_ids = fields.One2many(comodel_name="property.floorplan", inverse_name="property_id", string="Floor Plans")

connectivity_ids = fields.One2many(comodel_name="property.connectivity", inverse_name="property_id",
string="Nearby Connectivities")

is_published = fields.Boolean("Published on Website", default=False)
website_url = fields.Char("Website URL")
website_published_date = fields.Datetime("Published Date")

website_short_description = fields.Char("Short Description")
website_long_description = fields.Html("Long Description")
website_banner = fields.Image("Website Banner")

maintenance_count = fields.Integer(string="Maintenance", compute="_compute_maintenance_count")
lead_ids = fields.One2many(comodel_name='crm.lead', inverse_name='property_id', string='PropertyLeads')
lead_count = fields.Integer(string="Leads", compute="_compute_lead_count")

broker_id = fields.Many2one(comodel_name="res.partner", string="Broker / Agent",
domain="[('is_company','=',False)]")
broker_history_ids = fields.One2many(comodel_name="property.broker.history", inverse_name="property_id",
string="Brokers")
broker_bill_count = fields.Integer(string="Broker Bills", compute="_compute_broker_bill_count")

rent_contract_count = fields.Integer(compute="_compute_contract_counts", string="Rent Contracts")
sale_contract_count = fields.Integer(compute="_compute_contract_counts", string="Sale Contracts")
invoice_count = fields.Integer(string="Invoices", compute="_compute_invoice_count", store=False)

@api.model_create_multi
def create(self, vals_list):
for vals in vals_list:
sub_project_id = None
project_id = None
if vals.get("sub_project_id"):
sub_project_id = self.env["property.sub.project"].browse(vals["sub_project_id"])

if vals.get("project_id") and not vals.get("sub_project_id"):
project_id = self.env["property.project"].browse(vals["project_id"])
if project_id and project_id.code:
existing_count = self.search_count([("project_id", "=", project_id.id)])
next_number = 101 + existing_count
vals["name"] = f"{project_id.code}-{next_number}"

if not vals.get("access_token"):
vals["access_token"] = str(uuid.uuid4())
vals["code"] = self.env["ir.sequence"].next_by_code("property.detail") or "New"
if sub_project_id and sub_project_id.code:
existing_count = self.search_count([("sub_project_id", "=", sub_project_id.id)])
next_number = 101 + existing_count
vals["name"] = f"{sub_project_id.code}-{next_number}"

else:
pass

return super(PropertyDetails, self).create(vals_list)

def _get_active_rent_contract(self):
self.ensure_one()
return self.env["rent.contract"].search(
[("property_id", "=", self.id), ("state", "=", "running")], limit=1
)

def _get_active_sale_contract(self):
self.ensure_one()
return self.env["sale.contract"].search(
[("property_id", "=", self.id), ("state", "in", ("booked", "sold"))], limit=1
)

def _check_no_active_contract(self, target_state_label):
for rec in self:
active_rent = rec._get_active_rent_contract()
if active_rent:
raise UserError(
f"Cannot set '{rec.name}' to {target_state_label} while it has an active "
f"running rent contract ('{active_rent.name}'). Close, cancel, or expire the "
f"contract first."
)
active_sale = rec._get_active_sale_contract()
if active_sale:
raise UserError(
f"Cannot set '{rec.name}' to {target_state_label} while it has an active "
f"sale contract ('{active_sale.name}'). Cancel/refund the contract first."
)

def action_set_draft(self):
self._check_no_active_contract("Draft")
for rec in self:
rec.state = "draft"

def action_set_available(self):
self._check_no_active_contract("Available")
for rec in self:
rec.state = "available"

def action_set_on_rent(self):
for rec in self:
rec.state = "on_rent"

def action_set_on_sale(self):
for rec in self:
rec.state = "on_sale"

@api.depends("property_for", "pricing_type", "total_area", "price_per_area", "rent_amount", "sale_amount", )
def _compute_final_price(self):
for record in self:
record.final_price = 0.0

if record.property_for == "sale":
if record.pricing_type == "area_wise":
record.final_price = (record.price_per_area or 0.0) * (record.total_area or 0.0)
elif record.pricing_type == "fixed":
record.final_price = record.sale_amount or 0.0

elif record.property_for == "rent":
if record.pricing_type == "area_wise":
record.final_price = (record.price_per_area or 0.0) * (record.total_area or 0.0)
elif record.pricing_type == "fixed":
record.final_price = record.rent_amount or 0.0

@api.depends("charge_type", "total_area", "maintenance")
def _compute_total_maintenance(self):
for record in self:
if record.charge_type == "area_wise":
record.total_maintenance = (record.maintenance or 0.0) * (record.total_area or 0.0)
else:
record.total_maintenance = record.maintenance or 0.0

@api.depends("utility_service_ids.cost")
def _compute_total_utility_cost(self):
for record in self:
record.total_utility_cost = sum(record.utility_service_ids.mapped("cost"))

@api.depends("final_price", "total_maintenance", "total_utility_cost", "is_any_maintenance", "is_utility_services")
def _compute_total(self):
for record in self:
maintenance = record.total_maintenance if record.is_any_maintenance else 0.0
utilities = record.total_utility_cost if record.is_utility_services else 0.0

record.total_pricing = (record.final_price or 0.0) + maintenance + utilities

def action_open_map(self):
for rec in self:
if rec.latitude and rec.longitude:
url = f"https://www.google.com/maps?q={rec.latitude},{rec.longitude}"
else:
url = "https://www.google.com/maps"
return {
'type': 'ir.actions.act_url',
'target': 'new',
'url': url,
}

def action_create_maintenance(self):
self.ensure_one()
return {
'type': 'ir.actions.act_window',
'name': 'Maintenance Request',
'res_model': 'maintenance.request',
'view_mode': 'form',
'target': 'current',
'context': {
'default_name': f'Maintenance for {self.name}',
'default_property_id': self.id,
'default_request_date': fields.Datetime.now(),
}
}

def _compute_maintenance_count(self):
for rec in self:
rec.maintenance_count = self.env['maintenance.request'].search_count([('property_id', '=', rec.id)])

def action_view_maintenance_request(self):
self.ensure_one()
action = self.env.ref('maintenance.hr_equipment_request_action').read()[0]
action['domain'] = [('property_id', '=', self.id)]
action['context'] = {
'default_property_id': self.id,
'default_name': f'Maintenance for {self.name}',
}
return action

def action_create_leads(self):
self.ensure_one()
sequence = self.env['ir.sequence'].next_by_code('crm.lead') or 'New'
return {
'type': 'ir.actions.act_window',
'name': 'Create Lead',
'res_model': 'crm.lead',
'view_mode': 'form',
'target': 'current',
'context': {
'default_name': f'{self.name}-{sequence}',
'default_property_id': self.id,
'default_partner_id': self.landlord_id.id,
'default_description': f'Lead created from Property: {self.name}',
}
}

def _compute_lead_count(self):
for rec in self:
rec.lead_count = self.env['crm.lead'].search_count([('property_id', '=', rec.id)])

def action_view_leads(self):
return {
'type': 'ir.actions.act_window',
'name': 'Leads',
'res_model': 'crm.lead',
'view_mode': 'list,form',
'domain': [('property_id', '=', self.id)],
'context': {
'default_property_id': self.id,
'default_name': f'Lead for {self.name}',
}
}

def action_view_broker_bills(self):
self.ensure_one()
bill_ids = self.env['account.move'].search([
('property_id', '=', self.id),
('move_type', '=', 'in_invoice'),
])
return {
'name': 'Broker Bills',
'type': 'ir.actions.act_window',
'res_model': 'account.move',
'view_mode': 'list,form',
'domain': [('id', 'in', bill_ids.ids)],
'context': {'default_property_id': self.id},
}

def _compute_broker_bill_count(self):
for rec in self:
rec.broker_bill_count = self.env['account.move'].search_count([
('property_id', '=', rec.id),
('move_type', '=', 'in_invoice'), ])

def action_view_rent_contract(self):
self.ensure_one()
return {
'name': 'Rent Contracts',
'type': 'ir.actions.act_window',
'res_model': 'rent.contract',
'view_mode': 'list,form',
'domain': [('property_id', '=', self.id)],
'context': {'default_property_id': self.id},
}

def action_view_sale_contract(self):
self.ensure_one()
return {
'name': 'Sale Contracts',
'type': 'ir.actions.act_window',
'res_model': 'sale.contract',
'view_mode': 'list,form',
'domain': [('property_id', '=', self.id)],
'context': {'default_property_id': self.id},
}

def _compute_contract_counts(self):
for rec in self:
rec.rent_contract_count = self.env["rent.contract"].search_count([("property_id", "=", rec.id)])
rec.sale_contract_count = self.env["sale.contract"].search_count([("property_id", "=", rec.id)])

def action_view_invoices(self):
self.ensure_one()
return {'name': 'Invoices',
'type': 'ir.actions.act_window',
'res_model': 'account.move',
'view_mode': 'list,form',
'domain': [('property_id', '=', self.id), ('move_type', '=', 'out_invoice'), ],
'context': {'default_property_id': self.id, 'default_move_type': 'out_invoice'}, }

def _compute_invoice_count(self):
for rec in self:
rec.invoice_count = self.env["account.move"].search_count(
[("property_id", "=", rec.id), ("move_type", "=", "out_invoice")])

def action_send_property_brochure_mail(self):
self.ensure_one()

if not self.landlord_id or not self.landlord_id.email:
raise UserError("Please set a Landlord with a valid email address.")

report_id = self.env.ref('eg_property_management.report_property_detail_brochure_custom')
pdf_content, _ = report_id._render_qweb_pdf(report_id.report_name, [self.id])
attachment_id = self.env['ir.attachment'].create({
'name': f'Property_Brochure_{self.name}.pdf',
'type': 'binary',
'datas': base64.b64encode(pdf_content),
'res_model': 'property.detail',
'res_id': self.id,
'mimetype': 'application/pdf',
})
subject = f"Property Brochure - {self.name}"
body_html = f"""
<p>Dear {self.landlord_id.name},</p>
<p>Please find attached the brochure for the following property:</p>
<ul>
<li><strong>Property Name:</strong> {self.name}</li>
<li><strong>Property Type:</strong> {dict(self._fields['property_type'].selection).get(self.property_type)}</li>
<li><strong>For:</strong> {dict(self._fields['property_for'].selection).get(self.property_for)}</li>
<li><strong>Price:</strong> {self.final_price} {self.currency_id.symbol}</li>
<li><strong>Location:</strong> {self.city or ''} {self.state_id.name or ''}</li>
</ul>
<p>If you need any further details, feel free to contact us.</p>
<p>Thanks & Regards,<br/>
{self.env.user.name}</p>
"""
action = self.env['ir.actions.actions']._for_xml_id('mail.action_email_compose_message_wizard')
action['context'] = {
'default_model': 'property.detail',
'default_res_ids': [self.id],
'default_composition_mode': 'comment',
'default_partner_ids': [(6, 0, [self.landlord_id.id])],
'default_subject': subject,
'default_attachment_ids': [(6, 0, [attachment_id.id])],
'default_body': body_html,
}
return action
