# -*- coding: utf-8 -*-
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


RESIDENTIAL_TYPES = [
    ('studio', 'Studio'),
    ('1bed', '1 Bed'),
    ('2bed', '2 Bed'),
    ('3bed', '3 Bed'),
    ('penthouse', 'Penthouse'),
    ('office', 'Office'),
]

CONTRACT_STATES = [
    ('running', 'Running'),
    ('terminated', 'Terminated'),
    ('cancelled', 'Cancelled'),
    ('expired', 'Expired'),
]

UNIT_STATUSES = [
    ('occupied', 'Occupied'),
    ('vacant', 'Vacant'),
]


class PropertyUnit(models.Model):
    _name = "property.unit"
    _description = "Property Unit"
    _order = "name asc"

    name = fields.Char(string="Unit Name", required=True)
    unit_type = fields.Selection(
        selection=RESIDENTIAL_TYPES,
        string="Unit Type",
        required=True,
        default="1bed",
    )
    status = fields.Selection(
        selection=UNIT_STATUSES,
        string="Status",
        default="vacant",
        required=True,
    )
    area_sqft = fields.Float(string="Area (Sq. Ft.)", digits=(16, 2), default=750.0)
    price = fields.Monetary(
        string="Benchmark Rent / Price",
        currency_field="currency_id",
        help="Target benchmark rent per annum",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    contract_ids = fields.One2many(
        "property.contract",
        "property_id",
        string="Contracts",
    )

    def _sync_occupancy_status(self):
        for unit in self:
            running = self.env["property.contract"].search_count([
                ("property_id", "=", unit.id),
                ("state", "=", "running"),
            ])
            unit.status = "occupied" if running > 0 else "vacant"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._notify_dashboard_bus()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._notify_dashboard_bus()
        return res

    def unlink(self):
        self._notify_dashboard_bus()
        return super().unlink()

    @api.model
    def _notify_dashboard_bus(self):
        try:
            self.env["bus.bus"]._sendone(
                "property_dashboard_channel",
                "property_dashboard_update",
                {"type": "property_dashboard_update"},
            )
        except Exception:
            pass


class PropertyContract(models.Model):
    _name = "property.contract"
    _description = "Property Lease Contract"
    _order = "id desc"

    name = fields.Char(
        string="Contract Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    property_id = fields.Many2one(
        "property.unit",
        string="Property Unit",
        required=True,
        ondelete="restrict",
    )
    residential_type = fields.Selection(
        selection=RESIDENTIAL_TYPES,
        string="Residential Type",
        related="property_id.unit_type",
        store=True,
        readonly=False,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Tenant / Customer",
        required=True,
    )
    tenant_country_id = fields.Many2one(
        "res.country",
        string="Tenant Country",
        related="partner_id.country_id",
        store=True,
        readonly=False,
    )
    rent_amount = fields.Monetary(
        string="Rent Amount (Annual)",
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    duration_months = fields.Integer(string="Duration (Months)", default=12)
    start_date = fields.Date(
        string="Start Date",
        default=fields.Date.today,
        required=True,
    )
    end_date = fields.Date(
        string="End Date",
        compute="_compute_end_date",
        store=True,
        readonly=False,
    )
    days_remaining = fields.Integer(
        string="Days Remaining",
        compute="_compute_days_remaining",
    )
    state = fields.Selection(
        selection=CONTRACT_STATES,
        string="Status",
        default="running",
        required=True,
    )

    @api.depends("start_date", "duration_months")
    def _compute_end_date(self):
        for contract in self:
            if contract.start_date and contract.duration_months:
                contract.end_date = contract.start_date + relativedelta(months=contract.duration_months) - timedelta(days=1)
            elif not contract.end_date:
                contract.end_date = contract.start_date

    @api.depends("end_date", "state")
    def _compute_days_remaining(self):
        today = fields.Date.today()
        for contract in self:
            if contract.end_date and contract.state == "running":
                delta = (contract.end_date - today).days
                contract.days_remaining = max(delta, 0)
            else:
                contract.days_remaining = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("property.contract") or _("New")
        records = super().create(vals_list)
        for record in records:
            if record.property_id:
                record.property_id._sync_occupancy_status()
        self._notify_dashboard_bus()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals or "property_id" in vals:
            for record in self:
                if record.property_id:
                    record.property_id._sync_occupancy_status()
        self._notify_dashboard_bus()
        return res

    def unlink(self):
        units = self.mapped("property_id")
        res = super().unlink()
        for unit in units:
            unit._sync_occupancy_status()
        self._notify_dashboard_bus()
        return res

    @api.model
    def _notify_dashboard_bus(self):
        try:
            self.env["bus.bus"]._sendone(
                "property_dashboard_channel",
                "property_dashboard_update",
                {"type": "property_dashboard_update"},
            )
        except Exception:
            pass

    # =========================================================================
    # OPTIMIZED DASHBOARD RPC METRICS
    # =========================================================================
    @api.model
    def get_dashboard_metrics(self, filters=None):
        """
        Executive KPI summary, real-time Chart aggregations, and Top 50 directory
        with AED currency benchmarks and nationality analysis.
        """
        filters = filters or {}
        residential_type_filter = filters.get("residential_type")
        state_filter = filters.get("state")
        search_query = (filters.get("search") or "").strip().lower()

        # If property.contract is empty, auto-sync from eg_property_management if present
        if self.search_count([]) == 0:
            self._auto_bridge_eg_property_data()

        # Base domains
        unit_domain = []
        contract_domain = []

        if residential_type_filter and residential_type_filter != "all":
            unit_domain.append(("unit_type", "=", residential_type_filter))
            contract_domain.append(("residential_type", "=", residential_type_filter))

        # --- 1. KPI SUMMARY CARDS ---
        units = self.env["property.unit"].search(unit_domain)
        total_units = len(units)
        occupied_units = len(units.filtered(lambda u: u.status == "occupied"))
        vacant_units = total_units - occupied_units
        occupancy_rate = round((occupied_units / total_units * 100.0), 1) if total_units > 0 else 0.0

        all_contracts = self.search(contract_domain)
        running_contracts = all_contracts.filtered(lambda c: c.state == "running")
        active_contracts_count = len(running_contracts)

        # Total rent revenue for active leases (formatted in AED)
        total_rent_revenue = sum(running_contracts.mapped("rent_amount"))

        # Distinct tenant nationalities for active leases
        active_countries = running_contracts.mapped("tenant_country_id").filtered(lambda c: c)
        distinct_nationalities_count = len(set(active_countries.ids))

        # Currency formatting helper
        aed_currency = self.env["res.currency"].search([("name", "=", "AED")], limit=1)
        if not aed_currency:
            aed_currency = self.env.company.currency_id

        # --- 2. CHART AGGREGATIONS ---
        # A. Contracts by Status (Donut Chart)
        status_map = {
            "running": {"label": "Running", "color": "#10B981", "count": 0},
            "terminated": {"label": "Terminated", "color": "#EF4444", "count": 0},
            "cancelled": {"label": "Cancelled", "color": "#64748B", "count": 0},
            "expired": {"label": "Expired", "color": "#F59E0B", "count": 0},
        }
        for c in all_contracts:
            if c.state in status_map:
                status_map[c.state]["count"] += 1

        total_cnt = sum(item["count"] for item in status_map.values()) or 1
        contracts_by_status = {
            "labels": [v["label"] for v in status_map.values()],
            "counts": [v["count"] for v in status_map.values()],
            "percentages": [round((v["count"] / total_cnt) * 100.0, 1) for v in status_map.values()],
            "colors": [v["color"] for v in status_map.values()],
        }

        # B. Tenant Nationalities Mix (Horizontal Bar Chart)
        nationality_counts = defaultdict(int)
        country_code_map = {}
        for c in running_contracts:
            country = c.tenant_country_id
            name = country.name or "Unknown / Other"
            code = (country.code or "ae").lower()
            nationality_counts[name] += 1
            country_code_map[name] = code

        sorted_nationalities = sorted(nationality_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        active_total = len(running_contracts) or 1
        tenant_nationalities = {
            "labels": [item[0] for item in sorted_nationalities],
            "counts": [item[1] for item in sorted_nationalities],
            "percentages": [round((item[1] / active_total) * 100.0, 1) for item in sorted_nationalities],
            "codes": [country_code_map.get(item[0], "ae") for item in sorted_nationalities],
        }

        # C. Average Rent by Unit Type (Combo / Bar Chart)
        # Residential types order: Studio, 1 Bed, 2 Bed, 3 Bed, Penthouse, Office
        type_labels_dict = dict(RESIDENTIAL_TYPES)
        type_rents = defaultdict(list)
        type_benchmarks = defaultdict(list)

        for u in units:
            if u.price:
                type_benchmarks[u.unit_type].append(u.price)

        for c in running_contracts:
            if c.residential_type:
                type_rents[c.residential_type].append(c.rent_amount)

        ordered_types = ["studio", "1bed", "2bed", "3bed", "penthouse", "office"]
        avg_rent_values = []
        benchmark_values = []
        avg_rent_labels = []

        type_benchmark_averages = {}
        for t in ordered_types:
            avg_rent_labels.append(type_labels_dict.get(t, t))
            actual_avg = (sum(type_rents[t]) / len(type_rents[t])) if type_rents[t] else 0.0
            bench_avg = (sum(type_benchmarks[t]) / len(type_benchmarks[t])) if type_benchmarks[t] else actual_avg
            avg_rent_values.append(round(actual_avg, 2))
            benchmark_values.append(round(bench_avg, 2))
            type_benchmark_averages[t] = bench_avg or actual_avg or 1.0

        avg_rent_by_unit_type = {
            "labels": avg_rent_labels,
            "values": avg_rent_values,
            "benchmarks": benchmark_values,
            "unit_keys": ordered_types,
        }

        # D. Revenue Trends (Monthly rent collection stream)
        monthly_trends = defaultdict(float)
        # Build last 6 calendar months
        today = fields.Date.today()
        month_keys = []
        month_labels = []
        for i in range(5, -1, -1):
            m_date = today - relativedelta(months=i)
            key = m_date.strftime("%Y-%m")
            label = m_date.strftime("%b %Y")
            month_keys.append(key)
            month_labels.append(label)
            monthly_trends[key] = 0.0

        for c in running_contracts:
            if c.start_date:
                key = c.start_date.strftime("%Y-%m")
                if key in monthly_trends:
                    monthly_trends[key] += c.rent_amount
                else:
                    # Distribute rent across the running timeline
                    monthly_trends[month_keys[-1]] += (c.rent_amount / (c.duration_months or 12))

        revenue_trends = {
            "labels": month_labels,
            "values": [round(monthly_trends[k], 2) for k in month_keys],
        }

        # --- 3. RECENT DIRECTORY RECORDS (Top 50 Active Leases) ---
        directory_domain = [("state", "=", "running")]
        if residential_type_filter and residential_type_filter != "all":
            directory_domain.append(("residential_type", "=", residential_type_filter))
        if state_filter and state_filter != "all":
            # Override if custom state requested in directory filter
            directory_domain = [("state", "=", state_filter)]
            if residential_type_filter and residential_type_filter != "all":
                directory_domain.append(("residential_type", "=", residential_type_filter))

        directory_contracts = self.search(directory_domain, order="id desc", limit=100)

        records_data = []
        type_dict = dict(RESIDENTIAL_TYPES)
        state_dict = dict(CONTRACT_STATES)

        for c in directory_contracts:
            unit_name = c.property_id.name or "Unassigned"
            tenant_name = c.partner_id.name or "N/A"
            ref_name = c.name or ""

            # In-memory search filtering if text provided
            if search_query:
                combined = f"{ref_name} {unit_name} {tenant_name} {c.tenant_country_id.name or ''}".lower()
                if search_query not in combined:
                    continue

            # Benchmark comparison
            b_avg = type_benchmark_averages.get(c.residential_type, c.rent_amount)
            if b_avg and b_avg > 0:
                diff_pct = round(((c.rent_amount - b_avg) / b_avg) * 100.0, 1)
            else:
                diff_pct = 0.0

            records_data.append({
                "id": c.id,
                "name": c.name,
                "property_id": c.property_id.id,
                "unit_name": unit_name,
                "residential_type": c.residential_type,
                "unit_type": type_dict.get(c.residential_type, c.residential_type or "Unit"),
                "partner_id": c.partner_id.id,
                "tenant_name": tenant_name,
                "tenant_country_name": c.tenant_country_id.name or "United Arab Emirates",
                "tenant_country_code": (c.tenant_country_id.code or "ae").lower(),
                "rent_amount": c.rent_amount,
                "rent_amount_formatted": f"AED {c.rent_amount:,.2f}",
                "benchmark_rent": b_avg,
                "benchmark_rent_formatted": f"AED {b_avg:,.2f}",
                "benchmark_diff_pct": f"{'+' if diff_pct > 0 else ''}{diff_pct}%",
                "benchmark_diff_positive": diff_pct >= 0,
                "start_date": c.start_date.strftime("%Y-%m-%d") if c.start_date else "-",
                "end_date": c.end_date.strftime("%Y-%m-%d") if c.end_date else "-",
                "days_remaining": c.days_remaining,
                "days_remaining_class": (
                    "badge-danger" if c.days_remaining <= 30
                    else "badge-warning" if c.days_remaining <= 60
                    else "badge-success"
                ),
                "state": c.state,
                "state_label": state_dict.get(c.state, c.state.capitalize()),
                "state_badge_class": (
                    "badge-running" if c.state == "running"
                    else "badge-terminated" if c.state == "terminated"
                    else "badge-cancelled" if c.state == "cancelled"
                    else "badge-expired"
                ),
            })

            if len(records_data) >= 50:
                break

        return {
            "currency": {
                "name": "AED",
                "symbol": "AED",
                "position": "before",
            },
            "kpis": {
                "total_units": total_units,
                "occupied_units": occupied_units,
                "vacant_units": vacant_units,
                "occupancy_rate": occupancy_rate,
                "units_ratio_text": f"{occupied_units} / {total_units}",
                "vacant_alert": vacant_units > 0,
                "vacant_alert_status": "warning" if vacant_units > 5 else ("info" if vacant_units > 0 else "success"),
                "active_contracts_count": active_contracts_count,
                "total_rent_revenue": total_rent_revenue,
                "total_rent_revenue_formatted": f"AED {total_rent_revenue:,.2f}",
                "distinct_nationalities_count": distinct_nationalities_count,
            },
            "charts": {
                "contracts_by_status": contracts_by_status,
                "tenant_nationalities": tenant_nationalities,
                "avg_rent_by_unit_type": avg_rent_by_unit_type,
                "revenue_trends": revenue_trends,
            },
            "recent_contracts": records_data,
        }

    # =========================================================================
    # INTELLECTUAL DATA BRIDGE & DEMO SEEDER
    # =========================================================================
    @api.model
    def _auto_bridge_eg_property_data(self):
        """
        If eg_property_management (property.detail & rent.contract) exists,
        intelligently seed/mirror records into property.unit & property.contract.
        """
        if "property.detail" not in self.env or "rent.contract" not in self.env:
            return self.action_seed_demo_data()

        PropDetail = self.env["property.detail"]
        RentContract = self.env["rent.contract"]

        details = PropDetail.search([], limit=50)
        if not details:
            return self.action_seed_demo_data()

        unit_type_map = {
            "land": "office",
            "residential": "2bed",
            "commercial": "office",
            "industrial": "office",
        }

        unit_created_map = {}
        for detail in details:
            # Map residential type
            rtype = "2bed"
            if detail.residential_type:
                low = detail.residential_type.lower()
                if "studio" in low:
                    rtype = "studio"
                elif "1" in low or "one" in low:
                    rtype = "1bed"
                elif "2" in low or "two" in low:
                    rtype = "2bed"
                elif "3" in low or "three" in low:
                    rtype = "3bed"
                elif "pent" in low:
                    rtype = "penthouse"
                elif "office" in low or "commercial" in low:
                    rtype = "office"

            status = "occupied" if detail.state in ("on_rent", "rent") else "vacant"
            price = getattr(detail, "final_price", 0.0) or getattr(detail, "rent_amount", 0.0) or 95000.0

            unit = self.env["property.unit"].create({
                "name": detail.name or f"Unit {detail.id}",
                "unit_type": rtype,
                "status": status,
                "area_sqft": detail.total_area or 850.0,
                "price": price,
            })
            unit_created_map[detail.id] = unit

        # Bridge rent.contract
        rent_contracts = RentContract.search([], limit=100)
        state_map = {
            "draft": "running",
            "running": "running",
            "close": "terminated",
            "cancel": "cancelled",
            "expire": "expired",
        }

        for rc in rent_contracts:
            target_unit = unit_created_map.get(rc.property_id.id)
            if not target_unit:
                continue

            contract_state = state_map.get(rc.state, "running")
            self.create({
                "name": rc.name or _("New"),
                "property_id": target_unit.id,
                "partner_id": rc.tenant_id.id if rc.tenant_id else self.env.user.partner_id.id,
                "rent_amount": rc.rent or target_unit.price or 110000.0,
                "start_date": rc.start_date or fields.Date.today(),
                "end_date": rc.end_date or (fields.Date.today() + timedelta(days=365)),
                "duration_months": rc.duration or 12,
                "state": contract_state,
            })

    @api.model
    def action_seed_demo_data(self):
        """
        Creates a realistic, executive Dubai portfolio of 15 luxury units
        and 18 multinational lease contracts with UAE currency (AED).
        """
        if self.search_count([]) > 0:
            return True

        # Ensure Dubai / Global demo partners with nationalities
        countries = {
            "ae": self.env.ref("base.ae", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "AE")], limit=1),
            "gb": self.env.ref("base.uk", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "GB")], limit=1),
            "in": self.env.ref("base.in", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "IN")], limit=1),
            "fr": self.env.ref("base.fr", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "FR")], limit=1),
            "sa": self.env.ref("base.sa", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "SA")], limit=1),
            "de": self.env.ref("base.de", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "DE")], limit=1),
            "us": self.env.ref("base.us", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "US")], limit=1),
        }
        default_country = countries.get("ae") or self.env.company.country_id

        tenants_spec = [
            ("H.E. Tariq Al-Nuaimi", "ae"),
            ("James Bellingham", "gb"),
            ("Rajesh Varma", "in"),
            ("Sophie Moreau", "fr"),
            ("Prince Fahad Al-Saud", "sa"),
            ("Maximilian Becker", "de"),
            ("Alexander Vance", "us"),
            ("Fatima Al-Marzouqi", "ae"),
            ("Arjun Singhania", "in"),
            ("Charlotte Dubois", "fr"),
            ("Dr. Omar Al-Qasimi", "ae"),
            ("William Kensington", "gb"),
        ]

        tenant_records = []
        for name, c_code in tenants_spec:
            partner = self.env["res.partner"].create({
                "name": name,
                "country_id": countries.get(c_code, default_country).id if countries.get(c_code) else default_country.id,
                "customer_rank": 1,
            })
            tenant_records.append(partner)

        # 15 Luxury Units across Dubai
        units_spec = [
            ("Burj Crown Apt 1204", "1bed", 850.0, 95000.0),
            ("Burj Crown Apt 2108", "2bed", 1250.0, 145000.0),
            ("Downtown Views II 3401", "3bed", 1850.0, 220000.0),
            ("Downtown Views II 4202", "penthouse", 4200.0, 520000.0),
            ("Marina Gate 1 - Apt 805", "studio", 540.0, 72000.0),
            ("Marina Gate 1 - Apt 1602", "1bed", 890.0, 105000.0),
            ("Marina Gate 2 - Apt 2304", "2bed", 1320.0, 160000.0),
            ("Palm Views East Villa 12", "penthouse", 4800.0, 580000.0),
            ("Palm Jumeirah Apt 304", "2bed", 1400.0, 175000.0),
            ("Business Bay Tower A 402", "studio", 480.0, 64000.0),
            ("Business Bay Tower A 905", "1bed", 820.0, 92000.0),
            ("DIFC Gate Precinct Off 501", "office", 2600.0, 310000.0),
            ("DIFC Central Park Off 1202", "office", 1950.0, 240000.0),
            ("Creek Horizon Apt 1104", "2bed", 1280.0, 138000.0),
            ("Creek Horizon Apt 1902", "3bed", 1750.0, 195000.0),
        ]

        unit_recs = []
        for uname, utype, uarea, uprice in units_spec:
            unit = self.env["property.unit"].create({
                "name": uname,
                "unit_type": utype,
                "area_sqft": uarea,
                "price": uprice,
                "status": "vacant",
            })
            unit_recs.append(unit)

        today = fields.Date.today()

        # Seed 12 active contracts
        contracts_spec = [
            (unit_recs[0], tenant_records[0], 98000.0, today - relativedelta(months=2), 12, "running"),
            (unit_recs[1], tenant_records[1], 150000.0, today - relativedelta(months=4), 12, "running"),
            (unit_recs[2], tenant_records[2], 225000.0, today - relativedelta(months=1), 12, "running"),
            (unit_recs[3], tenant_records[4], 540000.0, today - relativedelta(months=5), 12, "running"),
            (unit_recs[4], tenant_records[3], 70000.0, today - relativedelta(months=3), 12, "running"),
            (unit_recs[5], tenant_records[5], 102000.0, today - relativedelta(months=6), 12, "running"),
            (unit_recs[6], tenant_records[6], 158000.0, today - relativedelta(months=2), 12, "running"),
            (unit_recs[7], tenant_records[7], 600000.0, today - relativedelta(months=7), 12, "running"),
            (unit_recs[8], tenant_records[8], 170000.0, today - relativedelta(months=1), 12, "running"),
            (unit_recs[9], tenant_records[9], 65000.0, today - relativedelta(months=8), 12, "running"),
            (unit_recs[11], tenant_records[10], 315000.0, today - relativedelta(months=4), 24, "running"),
            (unit_recs[12], tenant_records[11], 245000.0, today - relativedelta(months=3), 12, "running"),
            # Terminated, Cancelled, Expired for chart distribution
            (unit_recs[10], tenant_records[1], 90000.0, today - relativedelta(months=14), 12, "expired"),
            (unit_recs[13], tenant_records[2], 135000.0, today - relativedelta(months=6), 12, "terminated"),
            (unit_recs[14], tenant_records[3], 190000.0, today - relativedelta(months=2), 12, "cancelled"),
        ]

        for unit_rec, tenant_rec, rent, start_d, dur, st in contracts_spec:
            self.create({
                "property_id": unit_rec.id,
                "partner_id": tenant_rec.id,
                "rent_amount": rent,
                "start_date": start_d,
                "duration_months": dur,
                "state": st,
            })

        self._notify_dashboard_bus()
        return True
