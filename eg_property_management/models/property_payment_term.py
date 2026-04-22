from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PropertyPaymentTerm(models.Model):
    _name = "property.payment.term"
    _description = "Property Payment Term"
    _order = "interval_unit, interval_number, name"

    name = fields.Char(required=True)
    interval_number = fields.Integer(string="Interval", required=True, default=1)
    interval_unit = fields.Selection(
        [
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
            ("years", "Years"),
        ],
        string="Date Unit",
        required=True,
        default="months",
    )
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        "unique(name)",
        "Payment term name must be unique.",
    )

    @api.constrains("interval_number")
    def _check_interval_number(self):
        for rec in self:
            if rec.interval_number <= 0:
                raise ValidationError("Payment term interval must be greater than zero.")

    def _get_relativedelta(self):
        self.ensure_one()
        mapping = {
            "days": {"days": self.interval_number},
            "weeks": {"weeks": self.interval_number},
            "months": {"months": self.interval_number},
            "years": {"years": self.interval_number},
        }
        return relativedelta(**mapping[self.interval_unit])

    def _get_interval_days(self):
        self.ensure_one()
        factor_map = {
            "days": 1,
            "weeks": 7,
            "months": 30,
            "years": 365,
        }
        return self.interval_number * factor_map[self.interval_unit]

    @api.model
    def action_sync_existing_payment_terms(self):
        cr = self.env.cr
        term_records = {
            rec.name: rec.id
            for rec in self.sudo().search([("name", "in", ["Monthly", "Quarterly", "Yearly"])])
        }
        if not term_records:
            return

        cr.execute(
            """
            UPDATE rent_contract
               SET payment_term_id = %s,
                   payment_term = 'Monthly'
             WHERE payment_term_id IS NULL
               AND (payment_term = 'monthly' OR payment_term = 'Monthly')
            """,
            [term_records.get("Monthly")],
        )
        cr.execute(
            """
            UPDATE rent_contract
               SET payment_term_id = %s,
                   payment_term = 'Quarterly'
             WHERE payment_term_id IS NULL
               AND (payment_term = 'quarterly' OR payment_term = 'Quarterly')
            """,
            [term_records.get("Quarterly")],
        )
        cr.execute(
            """
            UPDATE rent_contract
               SET payment_term_id = %s,
                   payment_term = 'Yearly'
             WHERE payment_term_id IS NULL
               AND (payment_term = 'yearly' OR payment_term = 'Yearly')
            """,
            [term_records.get("Yearly")],
        )
        if term_records.get("Monthly"):
            cr.execute(
                """
                UPDATE rent_contract
                   SET payment_term_id = %s,
                       payment_term = COALESCE(NULLIF(payment_term, ''), 'Monthly')
                 WHERE payment_term_id IS NULL
                """,
                [term_records["Monthly"]],
            )
        cr.execute(
            """
            UPDATE rent_contract
               SET invoice_start_date = start_date
             WHERE invoice_start_date IS NULL
               AND start_date IS NOT NULL
            """
        )
