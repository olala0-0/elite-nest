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
        this.avgRentChartRef = useRef("avgRentChart");
        this.revenueTrendChartRef = useRef("revenueTrendChart");
        this.maintenanceChartRef = useRef("maintenanceChart");

        this._chartInstances = {};
        this._busCleanups = [];
        this._debounceTimer = null;

        this.state = useState({
            loading: true,
            realtimeConnected: false,
            lastUpdated: "",
            residentialType: "all",
            contractState: "all",
            searchQuery: "",
            pulseEffect: false,
            isEgProperty: true,
            multiCompany: {
                active_company_name: "",
                allowed_companies_count: 1,
                is_multi: false,
            },
            kpis: {
                total_units: 0,
                occupied_units: 0,
                vacant_units: 0,
                draft_units: 0,
                occupancy_rate: 0,
                units_ratio_text: "0 / 0",
                vacant_alert: false,
                vacant_alert_status: "info",
                active_contracts_count: 0,
                total_rent_revenue: 0,
                total_rent_revenue_formatted: "AED 0.00",
                distinct_nationalities_count: 0,
                maintenance_total: 0,
                maintenance_open: 0,
                maintenance_repaired: 0,
            },
            charts: {
                contracts_by_status: { labels: [], counts: [], percentages: [], colors: [] },
                tenant_nationalities: { labels: [], counts: [], percentages: [], codes: [] },
                avg_rent_by_unit_type: { labels: [], values: [], benchmarks: [] },
                revenue_trends: { labels: [], values: [] },
                maintenance_by_stage: { labels: [], counts: [] },
            },
            recentContracts: [],
            recentMaintenance: [],
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
                search: this.state.searchQuery,
            };

            const data = await this.orm.call("property.contract", "get_dashboard_metrics", [filters]);

            this.state.isEgProperty = data.is_eg_property;
            this.state.multiCompany = data.multi_company || {};
            this.state.kpis = data.kpis;
            this.state.charts = data.charts;
            this.state.recentContracts = data.recent_contracts || [];
            this.state.recentMaintenance = data.recent_maintenance || [];
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
    // LIGHT-MODE CHART.JS ENGINE
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
        this._renderAvgRentComboChart();
        this._renderRevenueTrendChart();
        this._renderMaintenanceChart();
    }

    /**
     * 1. Donut Chart: Contracts by Status (Lavender Theme)
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
                        backgroundColor: ["#d4bfe8", "#b399cc", "#8c6b99", "#5e426e"],
                        borderColor: "#272031",
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
                            color: "#b8a8cc",
                            font: { family: "Inter, sans-serif", size: 12, weight: "500" },
                            usePointStyle: true,
                            pointStyle: "circle",
                            padding: 14,
                        },
                    },
                    tooltip: {
                        backgroundColor: "#1b1622",
                        titleColor: "#ece3f5",
                        bodyColor: "#c2a9d9",
                        borderColor: "rgba(194, 169, 217, 0.25)",
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0) || 1;
                                const val = context.raw;
                                const pct = ((val / total) * 100).toFixed(1);
                                return ` ${context.label}: ${val} contracts (${pct}%)`;
                            },
                        },
                    },
                },
            },
        });
    }

    /**
     * 2. Horizontal Bar Chart: Tenant Nationalities (Lavender Theme)
     */
    _renderNationalitiesBarChart() {
        if (!this.nationalitiesChartRef.el) return;
        const chartData = this.state.charts.tenant_nationalities;
        if (!chartData || !chartData.labels || chartData.labels.length === 0) return;

        if (this._chartInstances.nationalities) {
            this._chartInstances.nationalities.destroy();
        }

        const lavenderPalette = ["#c2a9d9", "#b399cc", "#9e82ba", "#8c6b99", "#7d6199", "#6a4f85", "#5c4375", "#4a355e"];
        const ctx = this.nationalitiesChartRef.el.getContext("2d");
        this._chartInstances.nationalities = new window.Chart(ctx, {
            type: "bar",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: "Active Contracts",
                        data: chartData.counts,
                        backgroundColor: chartData.labels.map((_, i) => lavenderPalette[i % lavenderPalette.length]),
                        borderRadius: 6,
                        barThickness: 16,
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
                        backgroundColor: "#1b1622",
                        titleColor: "#ece3f5",
                        bodyColor: "#c2a9d9",
                        borderColor: "rgba(194, 169, 217, 0.25)",
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: (context) => {
                                const idx = context.dataIndex;
                                const pct = chartData.percentages[idx] || 0;
                                return ` ${context.raw} Contracts (${pct}% portfolio share)`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { color: "rgba(194, 169, 217, 0.08)" },
                        ticks: { color: "#b8a8cc", font: { size: 11 }, precision: 0 },
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: "#ece3f5", font: { size: 12, weight: "500" } },
                    },
                },
            },
        });
    }

    /**
     * 3. Bar / Benchmark Chart: Average Rent by Residential Type (Lavender Theme)
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
                        backgroundColor: "#c2a9d9",
                        hoverBackgroundColor: "#d4bfe8",
                        borderRadius: 6,
                        barPercentage: 0.6,
                    },
                    {
                        type: "line",
                        label: "Target Benchmark (AED)",
                        data: chartData.benchmarks,
                        borderColor: "#ece3f5",
                        backgroundColor: "#ece3f5",
                        borderWidth: 2,
                        pointBackgroundColor: "#b399cc",
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
                            color: "#b8a8cc",
                            usePointStyle: true,
                            pointStyle: "circle",
                            font: { size: 12 },
                        },
                    },
                    tooltip: {
                        backgroundColor: "#1b1622",
                        titleColor: "#ece3f5",
                        bodyColor: "#c2a9d9",
                        borderColor: "rgba(194, 169, 217, 0.25)",
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: (context) => ` ${context.dataset.label}: AED ${Number(context.raw).toLocaleString()}`,
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: "#ece3f5", font: { size: 11, weight: "500" } },
                    },
                    y: {
                        grid: { color: "rgba(194, 169, 217, 0.08)" },
                        ticks: {
                            color: "#b8a8cc",
                            callback: (v) => `${(v / 1000).toFixed(0)}k`,
                        },
                    },
                },
            },
        });
    }

    /**
     * 4. Revenue Timeline: Monthly Rent Trend (Lavender Theme)
     */
    _renderRevenueTrendChart() {
        if (!this.revenueTrendChartRef.el) return;
        const chartData = this.state.charts.revenue_trends;
        if (!chartData || !chartData.labels || chartData.labels.length === 0) return;

        if (this._chartInstances.revenueTrend) {
            this._chartInstances.revenueTrend.destroy();
        }

        const ctx = this.revenueTrendChartRef.el.getContext("2d");
        const gradient = ctx.createLinearGradient(0, 0, 0, 260);
        gradient.addColorStop(0, "rgba(194, 169, 217, 0.35)");
        gradient.addColorStop(1, "rgba(194, 169, 217, 0.0)");

        this._chartInstances.revenueTrend = new window.Chart(ctx, {
            type: "line",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: "Monthly Rent Cashflow (AED)",
                        data: chartData.values,
                        borderColor: "#c2a9d9",
                        borderWidth: 3,
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: "#c2a9d9",
                        pointBorderColor: "#272031",
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 7,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#1b1622",
                        titleColor: "#ece3f5",
                        bodyColor: "#c2a9d9",
                        borderColor: "rgba(194, 169, 217, 0.25)",
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: (context) => ` Rent: AED ${Number(context.raw).toLocaleString()}`,
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { color: "rgba(194, 169, 217, 0.05)" },
                        ticks: { color: "#b8a8cc", font: { size: 11 } },
                    },
                    y: {
                        grid: { color: "rgba(194, 169, 217, 0.08)" },
                        ticks: {
                            color: "#b8a8cc",
                            callback: (v) => `${(v / 1000).toFixed(0)}k`,
                        },
                    },
                },
            },
        });
    }

    /**
     * 5. Maintenance Requests by Stage (Lavender Theme)
     */
    _renderMaintenanceChart() {
        if (!this.maintenanceChartRef.el) return;
        const chartData = this.state.charts.maintenance_by_stage;
        if (!chartData || !chartData.labels || chartData.labels.length === 0) return;

        if (this._chartInstances.maintenance) {
            this._chartInstances.maintenance.destroy();
        }

        const ctx = this.maintenanceChartRef.el.getContext("2d");
        this._chartInstances.maintenance = new window.Chart(ctx, {
            type: "bar",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: "Requests",
                        data: chartData.counts,
                        backgroundColor: ["#d4bfe8", "#c2a9d9", "#a88cc4", "#8c6b99", "#5e426e"],
                        borderRadius: 6,
                        barThickness: 24,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#1b1622",
                        titleColor: "#ece3f5",
                        bodyColor: "#c2a9d9",
                        borderColor: "rgba(194, 169, 217, 0.25)",
                        borderWidth: 1,
                        padding: 12,
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: "#ece3f5", font: { size: 11, weight: "500" } },
                    },
                    y: {
                        grid: { color: "rgba(194, 169, 217, 0.08)" },
                        ticks: { color: "#b8a8cc", precision: 0 },
                    },
                },
            },
        });
    }

    // =========================================================================
    // UI INTERACTION HANDLERS & ACTIONS
    // =========================================================================
    onFilterResidentialType(ev) {
        this.state.residentialType = ev.target.value;
        this.loadDashboardData(true);
    }

    onFilterState(ev) {
        this.state.contractState = ev.target.value;
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

    openMaintenance(maintenanceId) {
        if (!maintenanceId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "maintenance.request",
            res_id: maintenanceId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllMaintenance() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Maintenance Requests",
            res_model: "maintenance.request",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
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

    createMaintenance() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Maintenance Request",
            res_model: "maintenance.request",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("property_realtime_dashboard", PropertyDashboard);
