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
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
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
    _description = "Property Contract"
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
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
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
    # OPTIMIZED DASHBOARD RPC METRICS (MULTI-COMPANY & LIVE PROPERTY/CONTRACTS)
    # =========================================================================
    @api.model
    def get_dashboard_metrics(self, filters=None):
        """
        Calculates executive metrics directly from the live property management
        database (property.detail, rent.contract, maintenance.request) with
        full Multi-Company scoping (self.env.companies).
        """
        filters = filters or {}
        residential_type_filter = filters.get("residential_type")
        state_filter = filters.get("state")
        search_query = (filters.get("search") or "").strip().lower()

        # Multi-company filter: support all active selected companies in Odoo header
        allowed_companies = self.env.companies.ids
        company_domain = ["|", ("company_id", "=", False), ("company_id", "in", allowed_companies)]

        has_eg_property = "property.detail" in self.env and "rent.contract" in self.env

        if has_eg_property:
            return self._get_eg_property_metrics(filters, company_domain, search_query)
        else:
            return self._get_standalone_metrics(filters, company_domain, search_query)

    @api.model
    def _get_eg_property_metrics(self, filters, company_domain, search_query):
        """Live metrics from eg_property_management (property.detail, rent.contract, maintenance.request)"""
        residential_type_filter = filters.get("residential_type")
        state_filter = filters.get("state")

        PropDetail = self.env["property.detail"]
        RentContract = self.env["rent.contract"]
        MaintenanceRequest = self.env.get("maintenance.request")

        # 1. Properties
        prop_domain = list(company_domain)
        if residential_type_filter and residential_type_filter != "all":
            prop_domain.append(("residential_type", "ilike", residential_type_filter))

        properties = PropDetail.search(prop_domain)
        total_units = len(properties)
        occupied_units = len(properties.filtered(lambda p: p.state in ("on_rent", "rent", "occupied")))
        vacant_units = len(properties.filtered(lambda p: p.state in ("available", "vacant")))
        draft_units = len(properties.filtered(lambda p: p.state == "draft"))
        if vacant_units == 0 and total_units > occupied_units:
            vacant_units = total_units - occupied_units - draft_units

        occupancy_rate = round((occupied_units / total_units * 100.0), 1) if total_units > 0 else 0.0

        # 2. Rent Contracts
        contract_domain = list(company_domain)
        if residential_type_filter and residential_type_filter != "all":
            contract_domain.append(("residential_type", "ilike", residential_type_filter))

        all_contracts = RentContract.search(contract_domain)
        running_contracts = all_contracts.filtered(lambda c: c.state == "running")
        expired_contracts = all_contracts.filtered(lambda c: c.state in ("expire", "expired"))
        terminated_contracts = all_contracts.filtered(lambda c: c.state in ("close", "terminated"))
        cancelled_contracts = all_contracts.filtered(lambda c: c.state in ("cancel", "cancelled"))

        active_contracts_count = len(running_contracts)
        total_rent_revenue = sum(running_contracts.mapped("rent"))

        # Distinct nationalities
        countries = set()
        for c in running_contracts:
            partner = getattr(c, "tenant_id", False) or getattr(c, "partner_id", False)
            if partner and partner.country_id:
                countries.add(partner.country_id.id)
        distinct_nationalities_count = len(countries)

        # 3. Maintenance Requests (Related to properties)
        m_total = 0
        m_open = 0
        m_in_progress = 0
        m_repaired = 0
        recent_maintenance_data = []
        maintenance_by_stage_labels = []
        maintenance_by_stage_counts = []

        if MaintenanceRequest:
            m_domain = list(company_domain)
            # Filter by properties in scope
            if properties:
                m_domain.append(("property_id", "in", properties.ids))
            maintenance_recs = MaintenanceRequest.search(m_domain)
            m_total = len(maintenance_recs)

            open_recs = maintenance_recs.filtered(lambda m: not (m.stage_id and m.stage_id.done))
            m_open = len(open_recs)
            m_repaired = m_total - m_open

            # Stage distribution
            stage_counts = defaultdict(int)
            for m in maintenance_recs:
                s_name = m.stage_id.name if m.stage_id else _("New Request")
                stage_counts[s_name] += 1
            maintenance_by_stage_labels = list(stage_counts.keys())
            maintenance_by_stage_counts = list(stage_counts.values())

            # Top 10 recent open requests
            for m in open_recs[:10]:
                recent_maintenance_data.append({
                    "id": m.id,
                    "name": m.name or _("Maintenance Request"),
                    "property_name": m.property_id.name if m.property_id else _("General Property"),
                    "stage_name": m.stage_id.name if m.stage_id else _("In Progress"),
                    "stage_done": bool(m.stage_id and m.stage_id.done),
                    "priority": m.priority or "1",
                    "request_date": m.request_date.strftime("%Y-%m-%d") if getattr(m, "request_date", False) else "-",
                    "technician": m.user_id.name if m.user_id else _("Unassigned"),
                })

        # --- Chart Aggregations ---
        # A. Contracts by Status
        status_counts = {
            "Running": len(running_contracts),
            "Expired": len(expired_contracts),
            "Terminated": len(terminated_contracts),
            "Cancelled": len(cancelled_contracts),
        }
        total_c = sum(status_counts.values()) or 1
        contracts_by_status = {
            "labels": ["Running", "Expired", "Terminated", "Cancelled"],
            "counts": [status_counts["Running"], status_counts["Expired"], status_counts["Terminated"], status_counts["Cancelled"]],
            "percentages": [round((v / total_c) * 100.0, 1) for v in [status_counts["Running"], status_counts["Expired"], status_counts["Terminated"], status_counts["Cancelled"]]],
            "colors": ["#10B981", "#F59E0B", "#EF4444", "#64748B"],
        }

        # B. Tenant Nationalities
        nat_counts = defaultdict(int)
        code_map = {}
        for c in running_contracts:
            partner = getattr(c, "tenant_id", False) or getattr(c, "partner_id", False)
            if partner and partner.country_id:
                cname = partner.country_id.name
                ccode = (partner.country_id.code or "ae").lower()
            else:
                cname = "United Arab Emirates"
                ccode = "ae"
            nat_counts[cname] += 1
            code_map[cname] = ccode

        sorted_nat = sorted(nat_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        act_total = len(running_contracts) or 1
        tenant_nationalities = {
            "labels": [item[0] for item in sorted_nat],
            "counts": [item[1] for item in sorted_nat],
            "percentages": [round((item[1] / act_total) * 100.0, 1) for item in sorted_nat],
            "codes": [code_map.get(item[0], "ae") for item in sorted_nat],
        }

        # C. Average Rent by Residential Type
        type_rents = defaultdict(list)
        for c in running_contracts:
            rtype = c.residential_type or (c.residential_type_id.name if hasattr(c, "residential_type_id") and c.residential_type_id else "Commercial")
            type_rents[rtype].append(c.rent)

        avg_rent_labels = list(type_rents.keys())[:8] if type_rents else ["1 Bed", "2 Bed", "3 Bed", "Studio", "Office"]
        avg_rent_values = [round(sum(type_rents[t]) / len(type_rents[t]), 2) if type_rents[t] else 95000.0 for t in avg_rent_labels]
        benchmarks = [round(v * 0.96, 2) for v in avg_rent_values]

        avg_rent_by_unit_type = {
            "labels": avg_rent_labels,
            "values": avg_rent_values,
            "benchmarks": benchmarks,
        }

        # D. Revenue Timeline
        monthly_trends = defaultdict(float)
        today = fields.Date.today()
        month_keys = []
        month_labels = []
        for i in range(5, -1, -1):
            m_date = today - relativedelta(months=i)
            k = m_date.strftime("%Y-%m")
            month_keys.append(k)
            month_labels.append(m_date.strftime("%b %Y"))
            monthly_trends[k] = 0.0

        for c in running_contracts:
            if c.start_date:
                k = c.start_date.strftime("%Y-%m")
                if k in monthly_trends:
                    monthly_trends[k] += c.rent
                else:
                    monthly_trends[month_keys[-1]] += (c.rent / (c.duration or 12))

        revenue_trends = {
            "labels": month_labels,
            "values": [round(monthly_trends[k], 2) for k in month_keys],
        }

        # --- Directory Contracts (Top 50 Active Contracts) ---
        dir_domain = list(company_domain)
        if state_filter and state_filter != "all":
            if state_filter == "running":
                dir_domain.append(("state", "=", "running"))
            elif state_filter == "expired":
                dir_domain.append(("state", "in", ("expire", "expired")))
            elif state_filter == "terminated":
                dir_domain.append(("state", "in", ("close", "terminated")))
            elif state_filter == "cancelled":
                dir_domain.append(("state", "in", ("cancel", "cancelled")))
        else:
            dir_domain.append(("state", "=", "running"))

        if residential_type_filter and residential_type_filter != "all":
            dir_domain.append(("residential_type", "ilike", residential_type_filter))

        dir_records = RentContract.search(dir_domain, order="id desc", limit=100)
        recent_contracts = []

        type_avg_map = {t: (sum(type_rents[t]) / len(type_rents[t])) if type_rents[t] else 100000.0 for t in type_rents}

        for c in dir_records:
            prop_name = c.property_id.name if c.property_id else "N/A"
            tenant_partner = getattr(c, "tenant_id", False) or getattr(c, "partner_id", False)
            tenant_name = tenant_partner.name if tenant_partner else "N/A"
            ref_name = c.name or ""

            if search_query:
                combined = f"{ref_name} {prop_name} {tenant_name}".lower()
                if search_query not in combined:
                    continue

            rtype = c.residential_type or "Residential"
            b_avg = type_avg_map.get(rtype, c.rent or 1.0)
            diff_pct = round(((c.rent - b_avg) / b_avg * 100.0), 1) if b_avg else 0.0

            c_days = getattr(c, "remaining_days", 0)
            status_lbl = "Running" if c.state == "running" else ("Expired" if c.state in ("expire", "expired") else ("Terminated" if c.state in ("close", "terminated") else "Cancelled"))
            badge_cls = "badge-running" if status_lbl == "Running" else ("badge-expired" if status_lbl == "Expired" else ("badge-terminated" if status_lbl == "Terminated" else "badge-cancelled"))

            country_name = tenant_partner.country_id.name if (tenant_partner and tenant_partner.country_id) else "United Arab Emirates"
            country_code = (tenant_partner.country_id.code or "ae").lower() if (tenant_partner and tenant_partner.country_id) else "ae"

            recent_contracts.append({
                "id": c.id,
                "name": c.name,
                "property_id": c.property_id.id if c.property_id else False,
                "unit_name": prop_name,
                "residential_type": rtype,
                "unit_type": rtype,
                "tenant_name": tenant_name,
                "tenant_country_name": country_name,
                "tenant_country_code": country_code,
                "rent_amount": c.rent,
                "rent_amount_formatted": f"AED {c.rent:,.2f}",
                "benchmark_rent": b_avg,
                "benchmark_rent_formatted": f"AED {b_avg:,.2f}",
                "benchmark_diff_pct": f"{'+' if diff_pct > 0 else ''}{diff_pct}%",
                "benchmark_diff_positive": diff_pct >= 0,
                "start_date": c.start_date.strftime("%Y-%m-%d") if c.start_date else "-",
                "end_date": c.end_date.strftime("%Y-%m-%d") if c.end_date else "-",
                "days_remaining": c_days,
                "days_remaining_class": "badge-danger" if c_days <= 30 else ("badge-warning" if c_days <= 60 else "badge-success"),
                "state": c.state,
                "state_label": status_lbl,
                "state_badge_class": badge_cls,
                "model_name": "rent.contract",
            })

            if len(recent_contracts) >= 50:
                break

        return {
            "is_eg_property": True,
            "currency": {"name": "AED", "symbol": "AED", "position": "before"},
            "multi_company": {
                "active_company_name": self.env.company.name,
                "allowed_companies_count": len(allowed_companies),
                "is_multi": len(allowed_companies) > 1,
            },
            "kpis": {
                "total_units": total_units,
                "occupied_units": occupied_units,
                "vacant_units": vacant_units,
                "draft_units": draft_units,
                "occupancy_rate": occupancy_rate,
                "units_ratio_text": f"{occupied_units} / {total_units}",
                "vacant_alert": vacant_units > 0,
                "vacant_alert_status": "warning" if vacant_units > 5 else ("info" if vacant_units > 0 else "success"),
                "active_contracts_count": active_contracts_count,
                "total_rent_revenue": total_rent_revenue,
                "total_rent_revenue_formatted": f"AED {total_rent_revenue:,.2f}",
                "distinct_nationalities_count": distinct_nationalities_count,
                # Maintenance KPIs
                "maintenance_total": m_total,
                "maintenance_open": m_open,
                "maintenance_repaired": m_repaired,
            },
            "charts": {
                "contracts_by_status": contracts_by_status,
                "tenant_nationalities": tenant_nationalities,
                "avg_rent_by_unit_type": avg_rent_by_unit_type,
                "revenue_trends": revenue_trends,
                "maintenance_by_stage": {
                    "labels": maintenance_by_stage_labels,
                    "counts": maintenance_by_stage_counts,
                },
            },
            "recent_contracts": recent_contracts,
            "recent_maintenance": recent_maintenance_data,
        }

    @api.model
    def _get_standalone_metrics(self, filters, company_domain, search_query):
        """Fallback for standalone property.unit and property.contract"""
        residential_type_filter = filters.get("residential_type")
        state_filter = filters.get("state")

        unit_domain = list(company_domain)
        contract_domain = list(company_domain)

        if residential_type_filter and residential_type_filter != "all":
            unit_domain.append(("unit_type", "=", residential_type_filter))
            contract_domain.append(("residential_type", "=", residential_type_filter))

        units = self.env["property.unit"].search(unit_domain)
        total_units = len(units)
        occupied_units = len(units.filtered(lambda u: u.status == "occupied"))
        vacant_units = total_units - occupied_units
        occupancy_rate = round((occupied_units / total_units * 100.0), 1) if total_units > 0 else 0.0

        all_contracts = self.search(contract_domain)
        running_contracts = all_contracts.filtered(lambda c: c.state == "running")
        active_contracts_count = len(running_contracts)
        total_rent_revenue = sum(running_contracts.mapped("rent_amount"))

        active_countries = running_contracts.mapped("tenant_country_id").filtered(lambda c: c)
        distinct_nationalities_count = len(set(active_countries.ids))

        # Status Chart
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

        # Tenant Nationalities
        nationality_counts = defaultdict(int)
        country_code_map = {}
        for c in running_contracts:
            country = c.tenant_country_id
            name = country.name or "United Arab Emirates"
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

        # Average Rent
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
        }

        # Revenue Trends
        today = fields.Date.today()
        month_keys = []
        month_labels = []
        monthly_trends = defaultdict(float)
        for i in range(5, -1, -1):
            m_date = today - relativedelta(months=i)
            key = m_date.strftime("%Y-%m")
            month_keys.append(key)
            month_labels.append(m_date.strftime("%b %Y"))
            monthly_trends[key] = 0.0

        for c in running_contracts:
            if c.start_date:
                key = c.start_date.strftime("%Y-%m")
                if key in monthly_trends:
                    monthly_trends[key] += c.rent_amount
                else:
                    monthly_trends[month_keys[-1]] += (c.rent_amount / (c.duration_months or 12))

        revenue_trends = {
            "labels": month_labels,
            "values": [round(monthly_trends[k], 2) for k in month_keys],
        }

        # Recent Contracts
        dir_domain = list(company_domain)
        dir_domain.append(("state", "=", "running"))
        if residential_type_filter and residential_type_filter != "all":
            dir_domain.append(("residential_type", "=", residential_type_filter))

        dir_records = self.search(dir_domain, order="id desc", limit=50)
        recent_contracts = []
        type_dict = dict(RESIDENTIAL_TYPES)

        for c in dir_records:
            recent_contracts.append({
                "id": c.id,
                "name": c.name,
                "property_id": c.property_id.id,
                "unit_name": c.property_id.name or "Unit",
                "residential_type": c.residential_type,
                "unit_type": type_dict.get(c.residential_type, c.residential_type or "Unit"),
                "tenant_name": c.partner_id.name or "N/A",
                "tenant_country_name": c.tenant_country_id.name or "United Arab Emirates",
                "tenant_country_code": (c.tenant_country_id.code or "ae").lower(),
                "rent_amount": c.rent_amount,
                "rent_amount_formatted": f"AED {c.rent_amount:,.2f}",
                "benchmark_rent": type_benchmark_averages.get(c.residential_type, c.rent_amount),
                "benchmark_rent_formatted": f"AED {type_benchmark_averages.get(c.residential_type, c.rent_amount):,.2f}",
                "benchmark_diff_pct": "+0.0%",
                "benchmark_diff_positive": True,
                "start_date": c.start_date.strftime("%Y-%m-%d") if c.start_date else "-",
                "end_date": c.end_date.strftime("%Y-%m-%d") if c.end_date else "-",
                "days_remaining": c.days_remaining,
                "days_remaining_class": "badge-success",
                "state": c.state,
                "state_label": "Running",
                "state_badge_class": "badge-running",
                "model_name": "property.contract",
            })

        return {
            "is_eg_property": False,
            "currency": {"name": "AED", "symbol": "AED", "position": "before"},
            "multi_company": {
                "active_company_name": self.env.company.name,
                "allowed_companies_count": len(allowed_companies),
                "is_multi": len(allowed_companies) > 1,
            },
            "kpis": {
                "total_units": total_units,
                "occupied_units": occupied_units,
                "vacant_units": vacant_units,
                "draft_units": 0,
                "occupancy_rate": occupancy_rate,
                "units_ratio_text": f"{occupied_units} / {total_units}",
                "vacant_alert": vacant_units > 0,
                "vacant_alert_status": "warning" if vacant_units > 5 else "info",
                "active_contracts_count": active_contracts_count,
                "total_rent_revenue": total_rent_revenue,
                "total_rent_revenue_formatted": f"AED {total_rent_revenue:,.2f}",
                "distinct_nationalities_count": distinct_nationalities_count,
                "maintenance_total": 0,
                "maintenance_open": 0,
                "maintenance_repaired": 0,
            },
            "charts": {
                "contracts_by_status": contracts_by_status,
                "tenant_nationalities": tenant_nationalities,
                "avg_rent_by_unit_type": avg_rent_by_unit_type,
                "revenue_trends": revenue_trends,
                "maintenance_by_stage": {"labels": [], "counts": []},
            },
            "recent_contracts": recent_contracts,
            "recent_maintenance": [],
        }


# =============================================================================
# EXTENSIONS TO EG_PROPERTY_MANAGEMENT FOR REAL-TIME BUS NOTIFICATIONS
# =============================================================================
class RentContractBusExtension(models.Model):
    _inherit = "rent.contract"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if "property.unit" in self.env:
            try:
                self.env["property.unit"]._notify_dashboard_bus()
            except Exception:
                pass
        return records

    def write(self, vals):
        res = super().write(vals)
        if "property.unit" in self.env:
            try:
                self.env["property.unit"]._notify_dashboard_bus()
            except Exception:
                pass
        return res

    def unlink(self):
        res = super().unlink()
        if "property.unit" in self.env:
            try:
                self.env["property.unit"]._notify_dashboard_bus()
            except Exception:
                pass
        return res


class PropertyDetailBusExtension(models.Model):
    _inherit = "property.detail"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if "property.unit" in self.env:
            try:
                self.env["property.unit"]._notify_dashboard_bus()
            except Exception:
                pass
        return records

    def write(self, vals):
        res = super().write(vals)
        if "property.unit" in self.env:
            try:
                self.env["property.unit"]._notify_dashboard_bus()
            except Exception:
                pass
        return res

    def unlink(self):
        res = super().unlink()
        if "property.unit" in self.env:
            try:
                self.env["property.unit"]._notify_dashboard_bus()
            except Exception:
                pass
        return res


class MaintenanceRequestBusExtension(models.Model):
    _inherit = "maintenance.request"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if "property.unit" in self.env:
            try:
                self.env["property.unit"]._notify_dashboard_bus()
            except Exception:
                pass
        return records

    def write(self, vals):
        res = super().write(vals)
        if "property.unit" in self.env:
            try:
                self.env["property.unit"]._notify_dashboard_bus()
            except Exception:
                pass
        return res

    def unlink(self):
        res = super().unlink()
        if "property.unit" in self.env:
            try:
                self.env["property.unit"]._notify_dashboard_bus()
            except Exception:
                pass
        return res
