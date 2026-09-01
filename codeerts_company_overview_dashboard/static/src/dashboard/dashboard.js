/** @odoo-module **/
import { Component, useState, useRef, onWillStart, onWillUnmount, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { cookie } from "@web/core/browser/cookie";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const PALETTE = ["#15a89b", "#0e8377", "#4bc0af", "#f5a623", "#7b61ff", "#e0567a", "#2d9cdb", "#27ae60"];
const numberFmt = (v) => (v == null ? v : Number(v).toLocaleString());

export class CompanyOverviewDashboard extends Component {
    static template = "codeerts_company_overview_dashboard.Dashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.isDark = cookie.get("color_scheme") === "dark";
        this._charts = [];
        this.state = useState({
            loading: true,
            data: null,
            preset: "last12",
            dateFrom: false,
            dateTo: false,
        });

        this._rangeProps = { type: "date", range: true, value: [false, false] };
        const getProps = () => this._rangeProps;
        useDateTimePicker({
            format: "yyyy-MM-dd",
            get pickerProps() { return getProps(); },
            onApply: (value) => this._onRangeApply(value),
        });

        onWillStart(async () => {
            this.currency = await this.orm.call("codeerts.company_overview.dashboard", "get_currency", []);
            await this._loadData();
            this.state.loading = false;
        });

        useEffect(
            () => { this._renderCharts(); return () => this._disposeCharts(); },
            () => [this.state.data],
        );

        onWillUnmount(() => this._disposeCharts());
    }

    async _loadData() {
        this.state.data = await this.orm.call(
            "codeerts.company_overview.dashboard", "get_data",
            [this.state.dateFrom, this.state.dateTo],
        );
    }

    async onDateChange(from, to) {
        this.state.dateFrom = from;
        this.state.dateTo = to;
        await this._loadData();
    }

    _isoDate(d) {
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    async onPreset(key) {
        const now = new Date();
        let from = new Date(now);
        if (key === "today") {
            from = new Date(now);
        } else if (key === "month") {
            from = new Date(now.getFullYear(), now.getMonth(), 1);
        } else if (key === "quarter") {
            from = new Date(now.getFullYear(), Math.floor(now.getMonth() / 3) * 3, 1);
        } else if (key === "ytd") {
            from = new Date(now.getFullYear(), 0, 1);
        } else {
            from = new Date(now);
            from.setMonth(from.getMonth() - 12);
        }
        this.state.preset = key;
        await this.onDateChange(this._isoDate(from), this._isoDate(now));
    }

    _onRangeApply(value) {
        const arr = Array.isArray(value) ? value : [value, value];
        const [start, end] = arr;
        if (start && end) {
            // Keep the seed props in sync with what was applied. The picker hook
            // re-reads params.pickerProps on EVERY render (computeBasePickerProps);
            // if this stayed [false, false] the next render would reset the picker
            // value and blank the date inputs, leaving no sign of the active range.
            this._rangeProps.value = [start, end];
            this.state.preset = "custom";
            this.onDateChange(start.toISODate(), end.toISODate());
        }
    }

    async onReset() {
        this._rangeProps.value = [false, false];
        if (this.rootRef.el) {
            this.rootRef.el.querySelectorAll(".codeerts_bd_date").forEach((i) => (i.value = ""));
        }
        await this.onPreset("last12");
    }

    money(v) {
        const c = this.currency || {};
        const n = Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
        return c.position === "after" ? `${n} ${c.symbol || ""}` : `${c.symbol || ""} ${n}`;
    }

    fmt(kpi) {
        const v = kpi.value || 0;
        if (kpi.format === "monetary") return this.money(v);
        if (kpi.format === "percent") return `${Math.round(v)}%`;
        if (kpi.format === "int") return Math.round(v).toLocaleString();
        return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
    }

    _disposeCharts() {
        this._charts.forEach((c) => {
            try { c.destroy(); } catch (e) { /* already gone */ }
        });
        this._charts = [];
    }

    _apexOptions(spec) {
        const onClick = (event, ctx, cfg) => {
            const i = cfg.dataPointIndex >= 0 ? cfg.dataPointIndex : cfg.seriesIndex;
            if (i != null && i >= 0) this._drill(spec, i);
        };
        const dark = this.isDark;
        const fore = dark ? "#c3cede" : "#5a6b7f";
        const base = {
            chart: { height: 300, toolbar: { show: false }, fontFamily: "inherit",
                     foreColor: fore, background: "transparent", animations: { enabled: true } },
            theme: { mode: dark ? "dark" : "light" },
            colors: PALETTE,
            dataLabels: { enabled: false },
            legend: { position: "bottom", labels: { colors: fore } },
            grid: { borderColor: dark ? "#33445a" : "#e7eef0" },
            tooltip: { theme: dark ? "dark" : "light", y: { formatter: (v) => (v != null ? v.toLocaleString() : v) } },
        };
        switch (spec.type) {
            case "area":
            case "bar":
                return {
                    ...base,
                    chart: { ...base.chart, type: spec.type, events: { dataPointSelection: onClick } },
                    series: spec.series,
                    xaxis: { categories: spec.labels },
                    yaxis: { labels: { formatter: numberFmt } },
                    stroke: { curve: "smooth", width: spec.type === "area" ? 2 : 0 },
                    fill: spec.type === "area"
                        ? { type: "gradient", gradient: { shadeIntensity: 1, opacityFrom: 0.5, opacityTo: 0.05 } }
                        : { opacity: 1 },
                    plotOptions: { bar: { borderRadius: 5, columnWidth: "55%" } },
                };
            case "hbar":
            case "funnel":
                return {
                    ...base,
                    chart: { ...base.chart, type: "bar", events: { dataPointSelection: onClick } },
                    series: spec.series,
                    xaxis: { categories: spec.labels, labels: { formatter: numberFmt } },
                    dataLabels: { enabled: true, formatter: numberFmt },
                    plotOptions: { bar: { horizontal: true, borderRadius: 5, distributed: true, barHeight: "70%" } },
                    legend: { show: false },
                };
            case "donut":
                return {
                    ...base,
                    chart: { ...base.chart, type: "donut", events: { dataPointSelection: onClick } },
                    series: (spec.series[0] && spec.series[0].data) || [],
                    labels: spec.labels,
                    dataLabels: { enabled: true, formatter: (val) => `${Math.round(val)}%` },
                    plotOptions: { pie: { donut: { size: "62%", labels: { show: true,
                        value: { formatter: numberFmt },
                        total: { show: true, label: "Total",
                                 formatter: (w) => numberFmt(w.globals.seriesTotals.reduce((a, b) => a + b, 0)) } } } } },
                };
            case "radial":
                return {
                    ...base,
                    chart: { ...base.chart, type: "radialBar" },
                    series: (spec.series[0] && spec.series[0].data) || [],
                    labels: spec.labels,
                    plotOptions: {
                        radialBar: {
                            hollow: { size: "58%" },
                            track: { background: dark ? "#2a3a4d" : "#e8f6f3" },
                            dataLabels: {
                                name: { fontSize: "13px", color: dark ? "#9fb0c0" : "#5a6b7f" },
                                value: { fontSize: "26px", fontWeight: 700, color: dark ? "#4bc0af" : "#0e8377", formatter: (v) => `${v}%` },
                            },
                        },
                    },
                };
            case "treemap":
                return {
                    ...base,
                    chart: { ...base.chart, type: "treemap", events: { dataPointSelection: onClick } },
                    legend: { show: false },
                    dataLabels: { enabled: true, style: { fontSize: "12px" } },
                    series: [{ data: spec.labels.map((l, i) => ({ x: l, y: spec.series[0].data[i] })) }],
                };
            case "heatmap":
                return {
                    ...base,
                    chart: { ...base.chart, type: "heatmap" },
                    series: spec.series,
                    dataLabels: { enabled: false },
                    colors: ["#15a89b"],
                    plotOptions: { heatmap: { radius: 4, enableShades: true, shadeIntensity: 0.6 } },
                };
            default:
                return {
                    ...base,
                    chart: { ...base.chart, type: "line" },
                    series: spec.series,
                    xaxis: { categories: spec.labels },
                };
        }
    }

    _renderCharts() {
        this._disposeCharts();
        const tab = this.state.data;
        if (!tab || !this.rootRef.el || !window.ApexCharts) return;
        for (const spec of tab.charts) {
            const el = this.rootRef.el.querySelector(`[data-chart='${spec.key}']`);
            if (!el) continue;
            const chart = new window.ApexCharts(el, this._apexOptions(spec));
            chart.render();
            this._charts.push(chart);
        }
    }

    _openRecords(model, name, domain) {
        if (!domain) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: model,
            domain: domain,
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    _drill(spec, index) {
        const domain = spec.domains && spec.domains[index];
        this._openRecords(spec.model, spec.title, domain);
    }

    onKpiClick(kpi) {
        this._openRecords(kpi.model, kpi.label, kpi.domain);
    }
}

registry.category("actions").add("codeerts_company_overview_dashboard", CompanyOverviewDashboard);
