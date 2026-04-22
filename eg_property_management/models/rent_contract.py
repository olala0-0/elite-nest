import math
from odoo import api, fields, models
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round

class RentContract(models.Model):
    _name = "rent.contract"
    _description = "Rent Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Sequence', default=lambda self: 'New')

    start_date = fields.Date(string="Start Date", default=fields.Date.today)
    end_date = fields.Date(string="End Date")
    duration = fields.Integer(string="Duration (Months)", compute="_compute_duration", store=True)
    contract_days = fields.Integer(string="Contract Days", compute="_compute_contract_days", store=True)
    remaining_days = fields.Integer(string="Remaining Days", compute="_compute_remaining_days")
    
    # Advanced Payment Terms (from main)
    payment_term_id = fields.Many2one(
        comodel_name="property.payment.term",
        string="Payment Term",
        required=True,
        default=lambda self: self.env.ref("eg_property_management.property_payment_term_monthly", raise_if_not_found=False),
    )
    payment_term = fields.Char(related="payment_term_id.name", string="Payment Term Name", store=True)
    payment_count = fields.Integer(string="Number of Payments", compute="_compute_payment_count", store=True)

    contract_type = fields.Selection(
        [('manual', 'Manual Installment'), ('auto', 'Auto Installment')],
        string="Installment Type",
        default="manual",
    )
    invoice_start_date = fields.Date(string="Invoice Start From", default=fields.Date.today)

    rent = fields.Monetary(
        string="Rent Amount",
        currency_field="currency_id",
        help="Total rent for the full contract period. Invoices are split by the number of payments.",
    )
    deposit = fields.Monetary(string="Security Deposit", currency_field="currency_id")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency",
                                 default=lambda self: self.env.company.currency_id)

    total_area = fields.Float(string="Total Area")
    usable_area = fields.Float(string="Usable Area")

    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    property_type = fields.Selection(
        [("land", "Land"), ("residential", "Residential"), ("commercial", "Commercial"), ("industrial", "Industrial")],
        string="Property Type", default='land')
    
    # Structured Residential Types (from main)
    residential_type_id = fields.Many2one(
        comodel_name="property.residential.type",
        string="Residential Type",
        related="property_id.residential_type_id",
        store=True,
        readonly=True,
    )
    residential_type = fields.Char(related="residential_type_id.name", string="Residential Type Text", store=True)
    type = fields.Char(related="residential_type_id.name", string="Residential Type Snapshot", store=True)

    # Address & Partners
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street2")
    city = fields.Char(string="City")
    state_id = fields.Many2one(comodel_name="res.country.state", string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one(comodel_name="res.country", string="Country")
    company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env.company)
    region_id = fields.Many2one(comodel_name="res.country.state", string="Region")

    tenant_id = fields.Many2one(comodel_name="res.partner", string="Tenant / Customer")
    tenant_phone = fields.Char(related="tenant_id.phone", string="Phone", readonly=True)
    tenant_email = fields.Char(related="tenant_id.email", string="Email", readonly=True)

    landlord_id = fields.Many2one(comodel_name="res.partner", string="Landlord")
    landlord_phone = fields.Char(related="landlord_id.phone", string="Phone", readonly=True)
    landlord_email = fields.Char(related="landlord_id.email", string="Email", readonly=True)

    # Maintenance & Items
    maintenance_type = fields.Selection([('once', 'Once'), ('recurring', 'Recurring')], string="Maintenance Type", default="once")
    charge_type = fields.Selection([("fixed", "Fixed"), ("area_wise", "Area Wise")], string="Charge Type", default="fixed")
    total_maintenance = fields.Monetary(string="Maintenance", currency_field="currency_id", tracking=True)

    installment_item_id = fields.Many2one(comodel_name="product.product", string="Installment Item")
    deposit_item_id = fields.Many2one(comodel_name="product.product", string="Deposit Item")
    deposit_invoice_id = fields.Many2one(comodel_name='account.move', string="Deposit Invoice", readonly=True)
    lead_id = fields.Many2one(comodel_name='crm.lead', string="Source Lead")

    # Penalties & Tax
    penalty_type = fields.Selection([('fixed', 'Fixed'), ('percent', 'Percent')], string="Penalty Type", default='