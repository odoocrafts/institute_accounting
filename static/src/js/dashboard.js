/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onPatched, useRef } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

export class AccountingDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.branchDueChartRef = useRef("branchDueChart");
        this.chartInstance = null;
        this.state = useState({
            data: {
                top_expenses: [],
                branch_metrics: [],
                cash_balance: 0,
                bank_balance: 0,
                fee_due: 0,
                income_month: 0,
                expense_month: 0,
                income_today: 0,
                expense_today: 0,
                currency_symbol: '$',
                is_manager: false,
            },
            loading: true,
            error: false,
        });

        onWillStart(async () => {
            await Promise.all([
                this.fetchData(),
                loadJS("/web/static/lib/Chart/Chart.js")
            ]);
        });

        onPatched(() => {
            this.renderCharts();
        });
    }

    async fetchData() {
        try {
            this.state.loading = true;
            const data = await this.orm.call(
                "institute.accounting.dashboard",
                "get_metrics",
                []
            );
            this.state.data = data;
        } catch (error) {
            console.error("Dashboard error:", error);
        } finally {
            this.state.loading = false;
        }
    }

    renderCharts() {
        if (!this.state.data.is_manager || !this.branchDueChartRef.el) return;
        
        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        const ctx = this.branchDueChartRef.el.getContext("2d");
        const labels = this.state.data.branch_metrics.map(b => b.name);
        const data = this.state.data.branch_metrics.map(b => b.fee_due);

        this.chartInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
                        '#858796', '#5a5c69', '#2e59d9', '#17a673', '#2c9faf'
                    ],
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    }
                }
            }
        });
    }

    formatNumber(number) {
        if (!number) return "0.00";
        return new Intl.NumberFormat('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(number);
    }

    openNewTransaction() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "institute.accounting.transaction",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

AccountingDashboard.template = "institute_accounting.Dashboard";

// Keep 'institute_accounting.dashboard' identical to what's mapped in the Action Tag
registry.category("actions").add("institute_accounting.dashboard", AccountingDashboard);
