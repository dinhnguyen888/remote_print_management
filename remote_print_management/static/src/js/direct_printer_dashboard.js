/** @odoo-module **/

import { Component, onWillStart, useState, useRef, onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

class DirectPrinterDashboard extends Component {
    static template = "remote_print_management.DirectPrinterDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            period: "today",
            status: "",
            client: "",
            search: "",
            data: { kpis: {}, chart: [], lanes: {}, agents: [], jobs: [], clients: [] },
        });

        this.chartRef = useRef("rpdChart");
        this.chart = null;

        onMounted(() => this.renderChart());
        onPatched(() => this.renderChart());
        onWillUnmount(() => {
            if (this.chart) this.chart.destroy();
        });

        onWillStart(async () => {
            await loadJS("https://cdn.jsdelivr.net/npm/apexcharts");
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("ir.attachment", "get_direct_printer_dashboard_data", [{
                period: this.state.period,
                print_status: this.state.status,
                search: this.state.search,
            }]);
        } catch (error) {
            this.notification.add("Unable to load dashboard data.", { type: "danger" });
            throw error;
        } finally {
            this.state.loading = false;
        }
    }

    get permissions() {
        return this.state.data.permissions || {
            show_kpis: true,
            show_chart: true,
            show_lanes: true,
            show_agents: true,
            show_recent_jobs: true,
            allow_quick_print: true,
            allow_export_report: true,
        };
    }

    exportReport() {
        window.location.href = "/web/printing/export_excel";
    }

    onActionClick(ev) {
        const name = ev.currentTarget.getAttribute("name");
        if (!name) return;
        this.action.doAction(name);
    }

    openJob(job) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ir.attachment",
            res_id: job.id,
            views: [[false, "form"]],
        });
    }

    laneJobs(name) {
        return this.state.data.lanes[name] || [];
    }

    get visibleAgents() {
        return (this.state.data.agents || []).slice(0, 10);
    }

    get visibleJobs() {
        return (this.state.data.jobs || []).slice(0, 10);
    }

    showMorePrinters() {
        this.action.doAction("remote_print_management.printer_details_action");
    }

    showMoreJobs() {
        this.action.doAction("remote_print_management.ir_attachment_print_action");
    }

    openLaneJobs(status) {
        const filterMap = {
            pending: "search_default_filter_pending",
            printing: "search_default_filter_printing",
            failed: "search_default_filter_failed",
        };
        const context = {};
        if (filterMap[status]) {
            context[filterMap[status]] = 1;
        }
        this.action.doAction("remote_print_management.ir_attachment_print_action", {
            additionalContext: context,
        });
    }

    async revokePrinter(agent) {
        if (window.confirm(`Are you sure you want to remove printer "${agent.name}"?`)) {
            try {
                await this.orm.call("printer.details", "action_revoke", [[agent.id]]);
                this.notification.add(`Printer ${agent.name} removed successfully.`, { type: "success" });
                await this.loadData();
            } catch (error) {
                this.notification.add("Failed to remove printer.", { type: "danger" });
            }
        }
    }

    renderChart() {
        if (!this.chartRef.el || !this.state.data.chart || !this.state.data.chart.length) return;

        if (this.chart) {
            this.chart.destroy();
        }

        const chartData = this.state.data.chart;
        const categories = chartData.map(c => c.label);
        const doneData = chartData.map(c => c.done);
        const printingData = chartData.map(c => c.printing);
        const failedData = chartData.map(c => c.failed);

        const options = {
            series: [
                { name: 'Done', data: doneData },
                { name: 'Printing', data: printingData },
                { name: 'Failed', data: failedData }
            ],
            chart: {
                type: 'bar',
                height: 280,
                stacked: false,
                toolbar: { show: false },
                animations: { enabled: true }
            },
            colors: ['#22c55e', '#3b82f6', '#ef4444'],
            plotOptions: {
                bar: {
                    horizontal: false,
                    borderRadius: 4,
                    columnWidth: '25%',
                },
            },
            xaxis: {
                categories: categories,
                labels: { style: { colors: '#6b7280', fontSize: '12px' } },
                axisBorder: { show: false },
                axisTicks: { show: false }
            },
            yaxis: {
                labels: { style: { colors: '#6b7280', fontSize: '12px' } },
            },
            legend: {
                position: 'top',
                horizontalAlign: 'right',
                markers: { radius: 12 }
            },
            fill: { opacity: 1 },
            dataLabels: { enabled: false },
            grid: {
                borderColor: '#f3f4f6',
                strokeDashArray: 4,
            }
        };

        this.chart = new ApexCharts(this.chartRef.el, options);
        this.chart.render();
    }

    stateLabel(state) {
        return { draft: "Draft", pending: "Pending", printing: "Printing", printed: "Printed", failed: "Failed" }[state] || state;
    }
}

registry.category("actions").add("remote_print_management.direct_printer_dashboard", DirectPrinterDashboard);
