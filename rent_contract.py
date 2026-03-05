from odoo import models, fields


class PropertyBrokerHistory(models.Model):
    _name = "property.broker.history"
    _description = "Property Broker History"

    property_id = fields.Many2one(comodel_name="property.detail", string="Property")
    broker_id = fields.Many2one(comodel_name="res.partner", string="Broker / Agent")
    commission = fields.Monetary(string="Commission")
    date = fields.Date(string="Date", default=fields.Date.today)
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id.id)
