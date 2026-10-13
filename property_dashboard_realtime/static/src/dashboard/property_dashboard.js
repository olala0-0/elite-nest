/** @odoo-module **/

import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class PropertyDashboard extends Component {
    static template = "property_dashboard_realtime.PropertyDashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = useService("bus_service");
        this.notification = useService("notification");

        // Chart canvas references
        this.statusChartRef = useRef("statusChart");
        this.nationalitiesChartRef = useRef("nationalitiesChart");
        this.facilityWorkOrdersChartRef = useRef("facilityWorkOrdersChart");
        this.slaGaugeChartRef = useRef("slaGaugeChart");
        this.avgRentChartRef = useRef("avgRentChart");
        this.revVsMaintChartRef = useRef("revVsMaintChart");

        this._chartInstances = {};
        this._busCleanups = [];
        this._debounceTimer = null;

        this.state = useState({
            loading: true,
            realtimeConnected: false,
            lastUpdated: "",
            residentialType: "all",
            contractState: "all",
            buildingBlock: "all",
            facilityType: "all",
            searchQuery: "",
            pulseEffect: false,
            isEgProperty: true,
            multiCompany: {
                active_company_name: "",
                allowed_companies_count: 1,
                is_multi: false,
            },
            kpis: {
                total_units: 193,
                occupied_units: 183,
                vacant_units: 10,
                occupancy_rate: 94.8,
                units_ratio_text: "183 / 193",
                vacant_badge: "Vacant: 10",
                vacant_alert: true,
                active_contracts_count: 163,
                active_contracts_subtitle: "8 properties vacant & ready for leasing",
                total_rent_revenue: 8731639.0,
                total_rent_revenue_formatted: "AED 8,731,639.00",
                revenue_subtitle: "Total annualized Rent stream in AED",
                distinct_nationalities_count: 18,
                maintenance_total: 126,
                maintenance_open: 14,
                maintenance_pending: 28,
                maintenance_repaired: 84,
                maintenance_subtitle: "Open / 28 Pending",
                utility_cost: 42150.0,
                utility_cost_formatted: "AED 42,150.00",
                utility_subtitle: "Energy & Water costs",
                utility_change_rate: -2.1,
                utility_change_formatted: "-2.1%",
                vendor_tasks_count: 8,
                vendor_tasks_badge: "Pending",
                vendor_tasks_subtitle: "External service provider tasks",
            },
            charts: {
                contracts_by_status: { labels: [], counts: [], percentages: [], colors: [] },
                tenant_nationalities: { labels: [], counts: [], percentages: [], codes: [] },
                facility_work_orders: { labels: [], counts: [], percentages: [], colors: [] },
                sla_data: { sla_met_pct: 89.2, sla_unmet_pct: 10.8, avg_response_hours: 3.4, gauge_values: [89.2, 10.8], colors: ["#8b68aa", "#e8e1f0"] },
                avg_rent_by_unit_type: { labels: [], values: [], benchmarks: [] },
                revenue_vs_maintenance: { labels: [], rent_inflows: [], maintenance_opex: [] },
            },
            assetHealth: [],
            upcomingExpiries: {
                lease_expiries: { next_30_days: 8, next_60_days: 15, next_90_days: 24, urgent_label: "8 Expiring soon" },
                planned_maintenance: { overhauls_pending: 12, overhauls_label: "12 major overhauls pending" },
            },
            workOrdersUrgent: [],
            recentContracts: [],
        });

        onWillStart(async () => {
            await this._ensureChartLib();
            await this.loadDashboardData(true);
        });

        onMounted(() => {
            this._setupBus();
            this._renderAllCharts();
        });

        useEffect(
            () => {
                this._renderAllCharts();
            },
            () => [this.state.charts, this.state.loading]
        );

        onWillUnmount(() => {
            this._teardownBus();
            this._destroyCharts();
        });
    }

    async _ensureChartLib() {
        if (window.Chart) return;
        try {
            const chartMod = await import("@web/core/chart/chart");
            if (chartMod && chartMod.Chart) {
                window.Chart = chartMod.Chart;
                return;
            }
        } catch (e) {}

        const candidateScripts = [
            "/web/static/lib/Chart/Chart.js",
            "/web/static/lib/chartjs/chartjs.js",
            "/web/static/lib/chartjs/chart.umd.min.js",
        ];
        for (const src of candidateScripts) {
            try {
                await loadJS(src);
                if (window.Chart) return;
            } catch (err) {}
        }
    }

    _setupBus() {
        if (!this.busService) return;
        try {
            this.busService.addChannel("property_dashboard_channel");

            if (typeof this.busService.subscribe === "function") {
                const unsubscribe = this.busService.subscribe("property_dashboard_update", () => {
                    this._onRealtimeBusEvent();
                });
                if (unsubscribe) this._busCleanups.push(unsubscribe);
            } else if (typeof this.busService.addEventListener === "function") {
                const listener = ({ detail: notifications }) => {
                    for (const notif of notifications) {
                        if (notif.type === "property_dashboard_update") {
                            this._onRealtimeBusEvent();
                            break;
                        }
                    }
                };
                this.busService.addEventListener("notification", listener);
                this._busCleanups.push(() => {
                    this.busService.removeEventListener("notification", listener);
                });
            }

            this.state.realtimeConnected = true;
        } catch (err) {
            console.warn("[PropertyDashboard] Bus setup warning:", err);
        }
    }

    _teardownBus() {
        for (const cleanup of this._busCleanups) {
            try {
                if (typeof cleanup === "function") cleanup();
            } catch (e) {}
        }
        this._busCleanups = [];
    }

    _onRealtimeBusEvent() {
        this.state.pulseEffect = true;
        setTimeout(() => {
            this.state.pulseEffect = false;
        }, 1200);

        if (this._debounceTimer) clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => {
            this.loadDashboardData(false);
        }, 300);
    }

    async loadDashboardData(showSpinner = false) {
        if (showSpinner) {
            this.state.loading = true;
        }
        try {
            const filters = {
                residential_type: this.state.residentialType,
                state: this.state.contractState,
                building_block: this.state.buildingBlock,
                facility_type: this.state.facilityType,
                search: this.state.searchQuery,
            };

            const data = await this.orm.call("property.contract", "get_dashboard_metrics", [filters]);

            this.state.isEgProperty = data.is_eg_property;
            this.state.multiCompany = data.multi_company || {};
            this.state.kpis = data.kpis;
            this.state.charts = data.charts;
            this.state.assetHealth = data.asset_health || [];
            this.state.upcomingExpiries = data.upcoming_expiries || {
                lease_expiries: { next_30_days: 8, next_60_days: 15, next_90_days: 24, urgent_label: "8 Expiring soon" },
                planned_maintenance: { overhauls_pending: 12, overhauls_label: "12 major overhauls pending" },
            };
            this.state.workOrdersUrgent = data.work_orders_urgent || [];
            this.state.recentContracts = data.recent_contracts || [];
            this.state.lastUpdated = new Date().toLocaleTimeString();
        } catch (err) {
            console.error("[PropertyDashboard] Error loading metrics:", err);
            this.notification.add("Failed to load real-time property metrics.", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    // =========================================================================
    // CHART.JS ENGINE (PALETTE: #c2a9d9 & VIOLET ON #ffffff CARDS)
    // =========================================================================
    _destroyCharts() {
        for (const key of Object.keys(this._chartInstances)) {
            if (this._chartInstances[key]) {
                try {
                    this._chartInstances[key].destroy();
                } catch (e) {}
                this._chartInstances[key] = null;
            }
        }
    }

    _renderAllCharts() {
        if (this.state.loading || !window.Chart) return;

        this._renderStatusDonutChart();
        this._renderNationalitiesBarChart();
        this._renderFacilityWorkOrdersChart();
        this._renderSlaGaugeChart();
        this._renderAvgRentComboChart();
        this._renderRevVsMaintChart();
    }

    /**
     * 1. Donut Chart: Contracts by Status
     */
    _renderStatusDonutChart() {
        if (!this.statusChartRef.el) return;
        const chartData = this.state.charts.contracts_by_status;
        if (!chartData || !chartData.labels || chartData.labels.length === 0) return;

        if (this._chartInstances.status) {
            this._chartInstances.status.destroy();
        }

        const ctx = this.statusChartRef.el.getContext("2d");
        this._chartInstances.status = new window.Chart(ctx, {
            type: "doughnut",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        data: chartData.counts,
                        backgroundColor: ["#8b68aa", "#b399cc", "#503966", "#3a254c"],
                        borderColor: "#ffffff",
                        borderWidth: 3,
                        hoverOffset: 6,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "68%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#4d3d5e",
                            font: { family: "Inter, sans-serif", size: 11, weight: "600" },
                            usePointStyle: true,
                            pointStyle: "circle",
                            padding: 10,
                        },
                    },
                    tooltip: {
                        backgroundColor: "#251c2e",
                        titleColor: "#ffffff",
                        bodyColor: "#c2a9d9",
                        borderColor: "rgba(139, 104, 170, 0.35)",
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0) || 1;
                                const val = context.raw;
                                const pct = ((val / total) * 100).toFixed(1);
                                return ` ${context.label}: ${val} (${pct}%)`;
                            },
                        },
                    },
                },
            },
        });
    }

    /**
     * 2. Horizontal Bar Chart: Tenant Nationalities
     */
    _renderNationalitiesBarChart() {
        if (!this.nationalitiesChartRef.el) return;
        const chartData = this.state.charts.tenant_nationalities;
        if (!chartData || !chartData.labels || chartData.labels.length === 0) return;

        if (this._chartInstances.nationalities) {
            this._chartInstances.nationalities.destroy();
        }

        const palette = ["#503966", "#72538f", "#8b68aa", "#9e82ba", "#b399cc", "#c2a9d9"];
        const ctx = this.nationalitiesChartRef.el.getContext("2d");
        this._chartInstances.nationalities = new window.Chart(ctx, {
            type: "bar",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: "Active Leases",
                        data: chartData.counts,
                        backgroundColor: chartData.labels.map((_, i) => palette[i % palette.length]),
                        borderRadius: 6,
                        barThickness: 14,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#251c2e",
                        titleColor: "#ffffff",
                        bodyColor: "#c2a9d9",
                        borderColor: "rgba(139, 104, 170, 0.35)",
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: (context) => {
                                const idx = context.dataIndex;
                                const pct = chartData.percentages ? chartData.percentages[idx] : 0;
                                return ` ${context.raw} Leases (${pct}%)`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { color: "rgba(194, 169, 217, 0.15)" },
                        ticks: { color: "#4d3d5e", font: { size: 10 }, precision: 0 },
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: "#1f1728", font: { size: 11, weight: "600" } },
                    },
                },
            },
        });
    }

    /**
     * 3. NEW: Facility & Work Order Status (Split/Stacked Doughnut)
     */
    _renderFacilityWorkOrdersChart() {
        if (!this.facilityWorkOrdersChartRef.el) return;
        const chartData = this.state.charts.facility_work_orders;
        if (!chartData || !chartData.labels || chartData.labels.length === 0) return;

        if (this._chartInstances.facilityWorkOrders) {
            this._chartInstances.facilityWorkOrders.destroy();
        }

        const ctx = this.facilityWorkOrdersChartRef.el.getContext("2d");
        this._chartInstances.facilityWorkOrders = new window.Chart(ctx, {
            type: "doughnut",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        data: chartData.counts,
                        backgroundColor: chartData.colors || ["#503966", "#72538f", "#8b68aa", "#a88cc4", "#c2a9d9"],
                        borderColor: "#ffffff",
                        borderWidth: 3,
                        hoverOffset: 6,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "65%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#4d3d5e",
                            font: { family: "Inter, sans-serif", size: 11, weight: "600" },
                            usePointStyle: true,
                            pointStyle: "circle",
                            padding: 8,
                        },
                    },
                    tooltip: {
                        backgroundColor: "#251c2e",
                        titleColor: "#ffffff",
                        bodyColor: "#c2a9d9",
                        borderColor: "rgba(139, 104, 170, 0.35)",
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0) || 1;
                                const val = context.raw;
                                const pct = ((val / total) * 100).toFixed(1);
                                return ` ${context.label}: ${val} Work Orders (${pct}%)`;
                            },
                        },
                    },
                },
            },
        });
    }

    /**
     * 4. NEW: SLA Resolution Rate Half-Gauge Chart
     */
    _renderSlaGaugeChart() {
        if (!this.slaGaugeChartRef.el) return;
        const sla = this.state.charts.sla_data || { sla_met_pct: 89.2, sla_unmet_pct: 10.8 };

        if (this._chartInstances.slaGauge) {
            this._chartInstances.slaGauge.destroy();
        }

        const ctx = this.slaGaugeChartRef.el.getContext("2d");
        this._chartInstances.slaGauge = new window.Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["SLA Met", "Pending / Outside SLA"],
                datasets: [
                    {
                        data: [sla.sla_met_pct, sla.sla_unmet_pct],
                        backgroundColor: ["#8b68aa", "#ede7f3"],
                        borderWidth: 0,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                rotation: -90,
                circumference: 180,
                cutout: "76%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#251c2e",
                        titleColor: "#ffffff",
                        bodyColor: "#c2a9d9",
                        callbacks: {
                            label: (context) => ` ${context.label}: ${context.raw}%`,
                        },
                    },
                },
            },
        });
    }

    /**
     * 5. Bar / Benchmark: Average Rent vs Benchmark by Type
     */
    _renderAvgRentComboChart() {
        if (!this.avgRentChartRef.el) return;
        const chartData = this.state.charts.avg_rent_by_unit_type;
        if (!chartData || !chartData.labels || chartData.labels.length === 0) return;

        if (this._chartInstances.avgRent) {
            this._chartInstances.avgRent.destroy();
        }

        const ctx = this.avgRentChartRef.el.getContext("2d");
        this._chartInstances.avgRent = new window.Chart(ctx, {
            type: "bar",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        type: "bar",
                        label: "Average Rent (AED)",
                        data: chartData.values,
                        backgroundColor: "#8b68aa",
                        hoverBackgroundColor: "#9d78bc",
                        borderRadius: 6,
                        barPercentage: 0.6,
                    },
                    {
                        type: "line",
                        label: "Target Benchmark (AED)",
                        data: chartData.benchmarks,
                        borderColor: "#503966",
                        backgroundColor: "#503966",
                        borderWidth: 2,
                        pointBackgroundColor: "#503966",
                        pointRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            color: "#4d3d5e",
                            usePointStyle: true,
                            pointStyle: "circle",
                            font: { size: 11, weight: "600" },
                        },
                    },
                    tooltip: {
                        backgroundColor: "#251c2e",
                        titleColor: "#ffffff",
                        bodyColor: "#c2a9d9",
                        padding: 10,
                        callbacks: {
                            label: (context) => ` ${context.dataset.label}: AED ${Number(context.raw).toLocaleString()}`,
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: "#1f1728", font: { size: 10, weight: "600" } },
                    },
                    y: {
                        grid: { color: "rgba(194, 169, 217, 0.15)" },
                        ticks: {
                            color: "#4d3d5e",
                            callback: (v) => `${(v / 1000).toFixed(0)}k`,
                        },
                    },
                },
            },
        });
    }

    /**
     * 6. NEW: Dual Chart - Monthly Revenue vs Maintenance OPEX
     */
    _renderRevVsMaintChart() {
        if (!this.revVsMaintChartRef.el) return;
        const chartData = this.state.charts.revenue_vs_maintenance;
        if (!chartData || !chartData.labels || chartData.labels.length === 0) return;

        if (this._chartInstances.revVsMaint) {
            this._chartInstances.revVsMaint.destroy();
        }

        const ctx = this.revVsMaintChartRef.el.getContext("2d");
        const gradient = ctx.createLinearGradient(0, 0, 0, 200);
        gradient.addColorStop(0, "rgba(194, 169, 217, 0.45)");
        gradient.addColorStop(1, "rgba(194, 169, 217, 0.0)");

        this._chartInstances.revVsMaint = new window.Chart(ctx, {
            type: "bar",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        type: "bar",
                        label: "Maintenance OPEX (AED)",
                        data: chartData.maintenance_opex,
                        backgroundColor: "#503966",
                        borderRadius: 6,
                        barPercentage: 0.5,
                        yAxisID: "y1",
                    },
                    {
                        type: "line",
                        label: "Rent Inflows (AED)",
                        data: chartData.rent_inflows,
                        borderColor: "#8b68aa",
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.3,
                        pointBackgroundColor: "#8b68aa",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        yAxisID: "y",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            color: "#4d3d5e",
                            usePointStyle: true,
                            pointStyle: "circle",
                            font: { size: 11, weight: "600" },
                        },
                    },
                    tooltip: {
                        backgroundColor: "#251c2e",
                        titleColor: "#ffffff",
                        bodyColor: "#c2a9d9",
                        padding: 10,
                        callbacks: {
                            label: (context) => ` ${context.dataset.label}: AED ${Number(context.raw).toLocaleString()}`,
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: "#1f1728", font: { size: 10 } },
                    },
                    y: {
                        type: "linear",
                        display: true,
                        position: "left",
                        grid: { color: "rgba(194, 169, 217, 0.15)" },
                        ticks: {
                            color: "#4d3d5e",
                            callback: (v) => `${(v / 1000).toFixed(0)}k`,
                        },
                    },
                    y1: {
                        type: "linear",
                        display: false,
                        position: "right",
                        grid: { drawOnChartArea: false },
                    },
                },
            },
        });
    }

    // =========================================================================
    // UI INTERACTION HANDLERS & WINDOW ACTIONS
    // =========================================================================
    onFilterResidentialType(ev) {
        this.state.residentialType = ev.target.value;
        this.loadDashboardData(true);
    }

    onFilterState(ev) {
        this.state.contractState = ev.target.value;
        this.loadDashboardData(true);
    }

    onFilterBuilding(ev) {
        this.state.buildingBlock = ev.target.value;
        this.loadDashboardData(true);
    }

    onFilterFacility(ev) {
        this.state.facilityType = ev.target.value;
        this.loadDashboardData(true);
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        if (this._debounceTimer) clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => {
            this.loadDashboardData(false);
        }, 300);
    }

    refreshDashboard() {
        this.loadDashboardData(true);
    }

    onActionClick(ev, contractId) {
        if (ev) ev.stopPropagation();
        this.openContract(contractId);
    }

    openContract(contractId) {
        if (!contractId) return;
        const resModel = this.state.isEgProperty ? "rent.contract" : "property.contract";
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            res_id: contractId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openProperty(propertyId) {
        if (!propertyId) return;
        const resModel = this.state.isEgProperty ? "property.detail" : "property.unit";
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            res_id: propertyId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllContracts() {
        const resModel = this.state.isEgProperty ? "rent.contract" : "property.contract";
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Rent Contracts",
            res_model: resModel,
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openAllProperties() {
        const resModel = this.state.isEgProperty ? "property.detail" : "property.unit";
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Properties",
            res_model: resModel,
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
        });
    }

    openWorkOrder(woId) {
        if (!woId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "property.maintenance.request",
            res_id: woId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllWorkOrders() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Facility Work Orders",
            res_model: "property.maintenance.request",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openUtilities() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Property Utilities & ESG",
            res_model: "property.utilities",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openAssets() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Facility Asset Health",
            res_model: "property.asset",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    createContract() {
        const resModel = this.state.isEgProperty ? "rent.contract" : "property.contract";
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Rent Contract",
            res_model: resModel,
            views: [[false, "form"]],
            target: "current",
        });
    }

    createWorkOrder() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Facility Work Order",
            res_model: "property.maintenance.request",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("property_realtime_dashboard", PropertyDashboard);
