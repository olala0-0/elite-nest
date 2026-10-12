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
            kpis: {
                total_units: 0,
                occupied_units: 0,
                vacant_units: 0,
                occupancy_rate: 0,
                units_ratio_text: "0 / 0",
                vacant_alert: false,
                vacant_alert_status: "info",
                active_contracts_count: 0,
                total_rent_revenue: 0,
                total_rent_revenue_formatted: "AED 0.00",
                distinct_nationalities_count: 0,
            },
            charts: {
                contracts_by_status: { labels: [], counts: [], percentages: [], colors: [] },
                tenant_nationalities: { labels: [], counts: [], percentages: [], codes: [] },
                avg_rent_by_unit_type: { labels: [], values: [], benchmarks: [] },
                revenue_trends: { labels: [], values: [] },
            },
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

    /**
     * Ensures Chart.js is loaded in the browser.
     * Tries native Odoo 19 asset bundle or fallback paths.
     */
    async _ensureChartLib() {
        if (window.Chart) return;
        try {
            const chartMod = await import("@web/core/chart/chart");
            if (chartMod && chartMod.Chart) {
                window.Chart = chartMod.Chart;
                return;
            }
        } catch (e) {
            // Proceed to asset loader
        }

        const candidateScripts = [
            "/web/static/lib/Chart/Chart.js",
            "/web/static/lib/chartjs/chartjs.js",
            "/web/static/lib/chartjs/chart.umd.min.js",
        ];
        for (const src of candidateScripts) {
            try {
                await loadJS(src);
                if (window.Chart) return;
            } catch (err) {
                // Continue to next candidate
            }
        }
    }

    /**
     * Subscribes to Odoo 19 bus.bus real-time channel.
     */
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
            console.warn("[PropertyDashboard] Bus subscription error:", err);
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
        // Trigger subtle flash animation
        this.state.pulseEffect = true;
        setTimeout(() => {
            this.state.pulseEffect = false;
        }, 1200);

        // Debounce reload
        if (this._debounceTimer) clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => {
            this.loadDashboardData(false);
        }, 300);
    }

    /**
     * Loads metrics from property.contract RPC
     */
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

            this.state.kpis = data.kpis;
            this.state.charts = data.charts;
            this.state.recentContracts = data.recent_contracts;
            this.state.lastUpdated = new Date().toLocaleTimeString();
        } catch (err) {
            console.error("[PropertyDashboard] Error loading metrics:", err);
            this.notification.add("Failed to load property dashboard metrics.", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    // =========================================================================
    // CHART.JS RENDERING ENGINE
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
                        backgroundColor: chartData.colors || ["#10B981", "#EF4444", "#64748B", "#F59E0B"],
                        borderColor: "#111827",
                        borderWidth: 3,
                        hoverOffset: 6,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "70%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#94A3B8",
                            font: { family: "Inter, sans-serif", size: 12 },
                            usePointStyle: true,
                            pointStyle: "circle",
                            padding: 16,
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        titleColor: "#F8FAFC",
                        bodyColor: "#94A3B8",
                        borderColor: "rgba(255, 255, 255, 0.1)",
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0) || 1;
                                const val = context.raw;
                                const pct = ((val / total) * 100).toFixed(1);
                                return ` ${context.label}: ${val} leases (${pct}%)`;
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

        const ctx = this.nationalitiesChartRef.el.getContext("2d");
        this._chartInstances.nationalities = new window.Chart(ctx, {
            type: "bar",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: "Active Leases",
                        data: chartData.counts,
                        backgroundColor: "#38BDF8",
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
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        titleColor: "#F8FAFC",
                        bodyColor: "#94A3B8",
                        borderColor: "rgba(255, 255, 255, 0.1)",
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: (context) => {
                                const idx = context.dataIndex;
                                const pct = chartData.percentages[idx] || 0;
                                return ` ${context.raw} Leases (${pct}% portfolio share)`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#64748B", font: { size: 11 }, precision: 0 },
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: "#CBD5E1", font: { size: 12, weight: "500" } },
                    },
                },
            },
        });
    }

    /**
     * 3. Bar / Line Combo Chart: Average Rent by Unit Type vs Benchmark
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
                        label: "Actual Avg Rent (AED)",
                        data: chartData.values,
                        backgroundColor: "#10B981",
                        borderRadius: 6,
                        barPercentage: 0.6,
                        order: 2,
                    },
                    {
                        type: "line",
                        label: "Benchmark Price (AED)",
                        data: chartData.benchmarks,
                        borderColor: "#F59E0B",
                        backgroundColor: "#F59E0B",
                        borderWidth: 2,
                        pointBackgroundColor: "#F59E0B",
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        order: 1,
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
                            color: "#94A3B8",
                            usePointStyle: true,
                            pointStyle: "circle",
                            font: { size: 12 },
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        titleColor: "#F8FAFC",
                        bodyColor: "#94A3B8",
                        borderColor: "rgba(255, 255, 255, 0.1)",
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
                        ticks: { color: "#CBD5E1", font: { size: 11 } },
                    },
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            color: "#64748B",
                            callback: (v) => `${(v / 1000).toFixed(0)}k`,
                        },
                    },
                },
            },
        });
    }

    /**
     * 4. Revenue Timeline: Monthly rent collection line/area
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
        gradient.addColorStop(0, "rgba(56, 189, 248, 0.35)");
        gradient.addColorStop(1, "rgba(56, 189, 248, 0.0)");

        this._chartInstances.revenueTrend = new window.Chart(ctx, {
            type: "line",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: "Monthly Lease Rent (AED)",
                        data: chartData.values,
                        borderColor: "#38BDF8",
                        borderWidth: 3,
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: "#38BDF8",
                        pointBorderColor: "#0F172A",
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
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        titleColor: "#F8FAFC",
                        bodyColor: "#94A3B8",
                        borderColor: "rgba(255, 255, 255, 0.1)",
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: (context) => ` Rent: AED ${Number(context.raw).toLocaleString()}`,
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: { color: "#CBD5E1", font: { size: 11 } },
                    },
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            color: "#64748B",
                            callback: (v) => `${(v / 1000).toFixed(0)}k`,
                        },
                    },
                },
            },
        });
    }

    // =========================================================================
    // UI INTERACTION HANDLERS
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
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "property.contract",
            res_id: contractId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openUnit(unitId) {
        if (!unitId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "property.unit",
            res_id: unitId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllContracts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Lease Contracts",
            res_model: "property.contract",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openAllUnits() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Property Units",
            res_model: "property.unit",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    createContract() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Lease Contract",
            res_model: "property.contract",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async seedDemoData() {
        this.state.loading = true;
        try {
            await this.orm.call("property.contract", "action_seed_demo_data", []);
            this.notification.add("Executive Dubai sample portfolio successfully seeded!", {
                type: "success",
            });
            await this.loadDashboardData(true);
        } catch (err) {
            console.error("Seed error:", err);
            this.notification.add("Failed to load sample portfolio.", { type: "danger" });
            this.state.loading = false;
        }
    }
}

registry.category("actions").add("property_realtime_dashboard", PropertyDashboard);
