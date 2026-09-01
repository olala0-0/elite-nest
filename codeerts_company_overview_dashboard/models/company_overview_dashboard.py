import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CompanyOverviewDashboard(models.TransientModel):
    _name = 'codeerts.company_overview.dashboard'
    _description = 'CODEerts Company Overview data provider'

    @api.model
    def get_currency(self):
        cur = self.env.company.currency_id
        return {'symbol': cur.symbol or cur.name or '',
                'position': cur.position or 'before',
                'decimals': cur.decimal_places if cur.decimal_places is not None else 2}

    @api.model
    def _can_read(self, model):
        """Non-raising read-access probe, portable across versions
        (v19/18 expose has_access(); v17 only check_access_rights())."""
        Model = self.env[model]
        if hasattr(Model, 'has_access'):
            return Model.has_access('read')
        return Model.check_access_rights('read', raise_exception=False)

    @api.model
    def _range(self, date_from, date_to):
        today = fields.Date.context_today(self)
        d_to = fields.Date.to_date(date_to) if date_to else today
        d_from = fields.Date.to_date(date_from) if date_from else (d_to - relativedelta(months=12))
        return d_from, d_to

    @api.model
    def _prev_range(self, d_from, d_to):
        span = d_to - d_from
        return (d_from - span - relativedelta(days=1), d_from - relativedelta(days=1))

    @api.model
    def _kpi(self, key, label, value, fmt, model, domain, prev=None):
        kpi = {'key': key, 'label': label, 'value': value or 0, 'format': fmt,
               'model': model, 'domain': domain}
        if prev is not None:
            cur, base = (value or 0), (prev or 0)
            pct = round((cur - base) / abs(base) * 100.0, 1) if base else (100.0 if cur else 0.0)
            kpi['delta'] = pct
            kpi['delta_dir'] = 'up' if pct > 0 else ('down' if pct < 0 else 'flat')
        return kpi

    @api.model
    def _chart(self, key, ctype, title, model, rows, series_name='Value'):
        return {
            'key': key, 'type': ctype, 'title': title, 'model': model,
            'labels': [r['label'] for r in rows],
            'series': [{'name': series_name, 'data': [r['value'] for r in rows]}],
            'domains': [r['domain'] for r in rows],
        }

    @api.model
    def _gauge(self, key, title, pct, model=None, domain=None):
        pct = max(0.0, min(100.0, round(pct or 0.0, 1)))
        return {'key': key, 'type': 'radial', 'title': title, 'model': model,
                'labels': [title], 'series': [{'name': title, 'data': [pct]}],
                'domains': [domain] if domain else None}

    @api.model
    def _count(self, model, domain):
        return self.env[model].search_count(domain)

    @api.model
    def _sum(self, model, domain, field):
        fld = self.env[model]._fields.get(field)
        if fld is None or not fld.store:
            return 0.0
        groups = self.env[model]._read_group(domain, [], [f'{field}:sum'])
        return (groups and groups[0][0]) or 0.0

    @api.model
    def _fmt_period(self, key):
        if not key:
            return 'None'
        if hasattr(key, 'strftime'):
            return key.strftime('%Y-%m')
        return str(key)[:7]

    @api.model
    def _grouped(self, model, domain, groupby, aggregate, limit=None):
        Model = self.env[model]
        is_gran = ':' in groupby
        field_name = groupby.split(':')[0]
        field = Model._fields.get(field_name)
        if field is None or not field.store:
            return []
        if aggregate != '__count':
            agg_field = Model._fields.get(aggregate.split(':')[0])
            if agg_field is None or not agg_field.store:
                return []
        sel = None
        if field.type == 'selection' and isinstance(field.selection, list):
            sel = dict(field.selection)
        rows = []
        try:
            groups = list(Model._read_group(domain, [groupby], [aggregate]))
        except ValueError:
            return []      # e.g. a granularity (day_of_week/hour_number) not supported on this version
        for group in groups:
            key, value = group[0], (group[1] or 0.0)
            if is_gran:
                rows.append({'label': self._fmt_period(key), 'value': value, 'domain': None})
            elif hasattr(key, '_name'):
                if key:
                    rows.append({'label': key.display_name or 'None', 'value': value,
                                 'domain': domain + [(field_name, '=', key.id)]})
                else:
                    rows.append({'label': 'None', 'value': value,
                                 'domain': domain + [(field_name, '=', False)]})
            elif key is False or key is None or key == '':
                rows.append({'label': 'None', 'value': value,
                             'domain': domain + [(field_name, '=', False)]})
            else:
                label = sel.get(key, str(key)) if sel else str(key)
                rows.append({'label': label, 'value': value,
                             'domain': domain + [(field_name, '=', key)]})
        if is_gran:
            rows.sort(key=lambda r: r['label'])
        elif limit:
            rows.sort(key=lambda r: r['value'], reverse=True)
            rows = rows[:limit]
        return rows

    _DOW = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    @api.model
    def _dow_label(self, key):
        try:
            return self._DOW[int(key)]
        except (TypeError, ValueError, IndexError):
            return str(key)

    @api.model
    def _heatmap(self, key, title, model, domain, gb_row, gb_col, aggregate,
                 row_labeller=None, col_labeller=None, row_order=None):
        try:
            grid, cols = {}, []
            for group in self.env[model]._read_group(domain, [gb_row, gb_col], [aggregate]):
                r_key, c_key, value = group[0], group[1], (group[2] or 0.0)
                r_lbl = row_labeller(r_key) if row_labeller else self._fmt_period(r_key)
                c_lbl = col_labeller(c_key) if col_labeller else self._fmt_period(c_key)
                grid.setdefault(r_lbl, {})[c_lbl] = value
                if c_lbl not in cols:
                    cols.append(c_lbl)
            if not grid:
                return None
            cols.sort()
            rows = row_order if row_order else sorted(grid)
            ordered = [r for r in rows if r in grid] + [r for r in grid if r not in (rows or [])]
            series = [{'name': r, 'data': [{'x': c, 'y': grid[r].get(c, 0)} for c in cols]} for r in ordered]
            return {'key': key, 'type': 'heatmap', 'title': title, 'model': model,
                    'labels': cols, 'series': series, 'domains': None}
        except Exception:
            _logger.warning("Dashboard: heatmap %s failed", key, exc_info=True)
            return None

    @api.model
    def _py_time_buckets(self, model, domain, date_field, agg, kind):
        """v17 fallback: Postgres has no day_of_week/hour_number granularity there, so
        bucket by hour (0-23) or weekday (0=Sun..6=Sat, matching Postgres DOW) in Python."""
        fname = None if agg == '__count' else agg.split(':')[0]
        buckets = {}
        for rec in self.env[model].search(domain):
            val = rec[date_field]
            if not val:
                continue
            if hasattr(val, 'hour'):
                val = fields.Datetime.context_timestamp(rec, val)
                k = val.hour if kind == 'hour' else (val.weekday() + 1) % 7
            else:
                if kind == 'hour':
                    continue
                k = (val.weekday() + 1) % 7
            buckets[k] = buckets.get(k, 0) + (rec[fname] if fname else 1)
        return buckets

    @api.model
    def _hourly(self, key, title, model, domain, date_field, agg, series_name='Sales'):
        buckets = {}
        try:
            for row in self.env[model]._read_group(domain, [f'{date_field}:hour_number'], [agg]):
                try:
                    buckets[int(row[0])] = row[1] or 0.0
                except (TypeError, ValueError):
                    continue
        except ValueError:
            buckets = self._py_time_buckets(model, domain, date_field, agg, 'hour')
        labels = [f'{h:02d}h' for h in range(24)]
        data = [buckets.get(h, 0) for h in range(24)]
        return {'key': key, 'type': 'bar', 'title': title, 'model': model,
                'labels': labels, 'series': [{'name': series_name, 'data': data}], 'domains': None}

    @api.model
    def _weekday(self, key, title, model, domain, date_field, agg, series_name='Count'):
        buckets = {}
        try:
            for row in self.env[model]._read_group(domain, [f'{date_field}:day_of_week'], [agg]):
                try:
                    buckets[int(row[0])] = row[1] or 0.0
                except (TypeError, ValueError):
                    continue
        except ValueError:
            buckets = self._py_time_buckets(model, domain, date_field, agg, 'weekday')
        data = [buckets.get(i, 0) for i in range(7)]
        return {'key': key, 'type': 'bar', 'title': title, 'model': model,
                'labels': list(self._DOW), 'series': [{'name': series_name, 'data': data}], 'domains': None}

    @api.model
    def _multi_trend(self, key, title, specs):
        per_series, all_labels = [], set()
        for name, model, domain, date_field, agg in specs:
            rows = self._grouped(model, domain, f'{date_field}:month', agg)
            data = {r['label']: r['value'] for r in rows}
            per_series.append((name, data))
            all_labels.update(data)
        labels = sorted(all_labels)
        series = [{'name': name, 'data': [data.get(l, 0) for l in labels]} for name, data in per_series]
        return {'key': key, 'type': 'area', 'title': title, 'model': None,
                'labels': labels, 'series': series, 'domains': None}

    @api.model
    def _states_present(self, model, wanted):
        """Return only those wanted state values that really exist on <model>.state
        in THIS version (keeps domains version-safe across v17/18/19)."""
        fld = self.env[model]._fields.get('state')
        valid = dict(fld.selection) if (fld and isinstance(fld.selection, list)) else {}
        return [s for s in wanted if s in valid]

    @api.model
    def get_data(self, date_from=False, date_to=False):
        d_from, d_to = self._range(date_from, date_to)
        kpis, charts = [], []
        p_from, p_to = self._prev_range(d_from, d_to)
        trend_specs, money_rows, workload_rows = [], [], []
        if 'sale.order' in self.env and self._can_read('sale.order'):
            dom = [('date_order', '>=', d_from), ('date_order', '<=', d_to), ('state', '=', 'sale')]
            prev = [('date_order', '>=', p_from), ('date_order', '<=', p_to), ('state', '=', 'sale')]
            total = self._sum('sale.order', dom, 'amount_total')
            kpis.append(self._kpi('ov_sales', 'Sales', total, 'monetary', 'sale.order', dom,
                                  prev=self._sum('sale.order', prev, 'amount_total')))
            trend_specs.append(('Sales', 'sale.order', dom, 'date_order', 'amount_total:sum'))
            money_rows.append(('Sales', total))
            charts.append(self._chart('ov_top_customers', 'hbar', 'Top Customers (Sales)', 'sale.order',
                          self._grouped('sale.order', dom, 'partner_id', 'amount_total:sum', limit=10), 'Sales'))
        if 'purchase.order' in self.env and self._can_read('purchase.order'):
            dom = [('date_order', '>=', d_from), ('date_order', '<=', d_to), ('state', '=', 'purchase')]
            prev = [('date_order', '>=', p_from), ('date_order', '<=', p_to), ('state', '=', 'purchase')]
            total = self._sum('purchase.order', dom, 'amount_total')
            kpis.append(self._kpi('ov_purchase', 'Spend', total, 'monetary', 'purchase.order', dom,
                                  prev=self._sum('purchase.order', prev, 'amount_total')))
            trend_specs.append(('Spend', 'purchase.order', dom, 'date_order', 'amount_total:sum'))
            money_rows.append(('Purchase', total))
        if 'stock.quant' in self.env and self._can_read('stock.quant'):
            dom = [('location_id.usage', '=', 'internal')]
            kpis.append(self._kpi('ov_stock', 'On-hand Units', self._sum('stock.quant', dom, 'quantity'),
                                  'float', 'stock.quant', dom))
        if 'stock.picking' in self.env and self._can_read('stock.picking'):
            dd = [('picking_type_id.code', '=', 'outgoing'), ('state', 'not in', ('done', 'cancel'))]
            workload_rows.append(('Deliveries Due', self._count('stock.picking', dd)))
        if 'mrp.production' in self.env and self._can_read('mrp.production'):
            dom = [('state', 'in', ('confirmed', 'progress', 'to_close'))]
            c = self._count('mrp.production', dom)
            kpis.append(self._kpi('ov_mrp', 'MOs In Progress', c, 'int', 'mrp.production', dom))
            workload_rows.append(('MOs In Progress', c))
        if 'crm.lead' in self.env and self._can_read('crm.lead'):
            dom = [('type', '=', 'opportunity'), ('active', '=', True)]
            kpis.append(self._kpi('ov_crm', 'Pipeline', self._sum('crm.lead', dom, 'expected_revenue'),
                                  'monetary', 'crm.lead', dom))
            workload_rows.append(('Open Opps', self._count('crm.lead', dom)))
            newl = [('create_date', '>=', d_from), ('create_date', '<=', d_to)]
            charts.append(self._chart('ov_leads_trend', 'area', 'Leads Created', 'crm.lead',
                          self._grouped('crm.lead', newl, 'create_date:month', '__count'), 'Leads'))
            charts.append(self._chart('ov_pipeline_by_stage', 'funnel', 'Pipeline by Stage', 'crm.lead',
                          self._grouped('crm.lead', dom, 'stage_id', 'expected_revenue:sum'), 'Expected'))
        if 'project.task' in self.env and self._can_read('project.task'):
            dom = [('state', 'not in', ('1_done', '1_canceled'))]
            c = self._count('project.task', dom)
            kpis.append(self._kpi('ov_project', 'Open Tasks', c, 'int', 'project.task', dom))
            workload_rows.append(('Open Tasks', c))
            charts.append(self._chart('ov_tasks_by_project', 'hbar', 'Open Tasks by Project', 'project.task',
                          self._grouped('project.task', dom, 'project_id', '__count', limit=10)))
        if 'pos.order' in self.env and self._can_read('pos.order'):
            _done = self._states_present('pos.order', ('paid', 'done', 'invoiced'))
            dom = [('date_order', '>=', d_from), ('date_order', '<=', d_to), ('state', 'in', _done)]
            prev = [('date_order', '>=', p_from), ('date_order', '<=', p_to), ('state', 'in', _done)]
            total = self._sum('pos.order', dom, 'amount_total')
            kpis.append(self._kpi('ov_pos', 'POS Sales', total, 'monetary', 'pos.order', dom,
                                  prev=self._sum('pos.order', prev, 'amount_total')))
            trend_specs.append(('POS', 'pos.order', dom, 'date_order', 'amount_total:sum'))
            money_rows.append(('POS', total))
        if 'hr.expense' in self.env and self._can_read('hr.expense'):
            dom = [('date', '>=', d_from), ('date', '<=', d_to), ('state', '!=', 'refused')]
            total = self._sum('hr.expense', dom, 'total_amount')
            kpis.append(self._kpi('ov_expense', 'Expenses', total, 'monetary', 'hr.expense', dom))
            money_rows.append(('Expenses', total))
        if 'account.move' in self.env and self._can_read('account.move'):
            ar_open = [('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted'),
                       ('payment_state', 'in', ('not_paid', 'partial'))]
            ap_open = [('move_type', 'in', ('in_invoice', 'in_refund')), ('state', '=', 'posted'),
                       ('payment_state', 'in', ('not_paid', 'partial'))]
            kpis.append(self._kpi('ov_ar', 'AR Outstanding',
                                  self._sum('account.move', ar_open, 'amount_residual_signed'),
                                  'monetary', 'account.move', ar_open))
            kpis.append(self._kpi('ov_ap', 'AP Outstanding',
                                  -self._sum('account.move', ap_open, 'amount_residual_signed'),
                                  'monetary', 'account.move', ap_open))
            charts.append({'key': 'ov_ar_ap', 'type': 'bar', 'title': 'AR vs AP Outstanding', 'model': None,
                           'labels': ['AR Outstanding', 'AP Outstanding'],
                           'series': [{'name': 'Amount', 'data': [
                               self._sum('account.move', ar_open, 'amount_residual_signed'),
                               -self._sum('account.move', ap_open, 'amount_residual_signed')]}], 'domains': None})
        if 'hr.employee' in self.env and self._can_read('hr.employee'):
            hdom = [('active', '=', True)]
            kpis.append(self._kpi('ov_headcount', 'Employees', self._count('hr.employee', hdom),
                                  'int', 'hr.employee', hdom))
        overview = []
        if trend_specs:
            overview.append(self._multi_trend('cash_flow', 'Revenue & Spend Trend', trend_specs))
        if len(money_rows) >= 2:
            overview.append({'key': 'money_by_area', 'type': 'bar', 'title': 'Money by Area', 'model': None,
                             'labels': [r[0] for r in money_rows],
                             'series': [{'name': 'Amount', 'data': [r[1] for r in money_rows]}], 'domains': None})
        if len(workload_rows) >= 2:
            overview.append({'key': 'workload', 'type': 'donut', 'title': 'Open Workload', 'model': None,
                             'labels': [r[0] for r in workload_rows],
                             'series': [{'name': 'Count', 'data': [r[1] for r in workload_rows]}], 'domains': None})
        charts = overview + charts
        return {'kpis': kpis, 'charts': charts}
