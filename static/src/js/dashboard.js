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
        this.branchIncomeChartRef = useRef("branchIncomeChart");
        this.chartInstance = null;
        this.incomeChartInstance = null;
        this.state = useState({
            period: "previous_month",
            data: {
                top_expenses: [],
                branch_metrics: [],
                branch_totals: {
                    cash_balance: 0,
                    bank_balance: 0,
                    total_balance: 0,
                    fee_due: 0,
                    income: 0,
                    expense: 0,
                    profit: 0,
                },
                cash_balance: 0,
                bank_balance: 0,
                fee_due: 0,
                income_month: 0,
                expense_month: 0,
                income_today: 0,
                expense_today: 0,
                currency_symbol: '₹',
                is_manager: false,
                period_label: "Previous Month",
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

        onMounted(() => {
            this.renderCharts();
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
                [this.state.period]
            );
            this.state.data = data;
        } catch (error) {
            console.error("Dashboard error:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async onPeriodChange(ev) {
        this.state.period = ev.target.value;
        await this.fetchData();
    }

    printDashboard() {
        this.action.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: "institute_accounting.report_dashboard",
            data: { period: this.state.period }
        });
    }

    renderCharts() {
        if (this.chartInstance) {
            this.chartInstance.destroy();
        }
        if (this.incomeChartInstance) {
            this.incomeChartInstance.destroy();
        }

        const isManager = this.state.data.is_manager;

        // Chart 1: Fee Due Pie Chart
        if (this.branchDueChartRef.el) {
            const ctx = this.branchDueChartRef.el.getContext("2d");
            let labels = [];
            let data = [];

            if (isManager) {
                if (!this.state.data.branch_metrics || this.state.data.branch_metrics.length === 0) return;
                labels = this.state.data.branch_metrics.map(b => b.name);
                data = this.state.data.branch_metrics.map(b => b.fee_due);
            } else {
                if (!this.state.data.course_metrics || this.state.data.course_metrics.length === 0) return;
                labels = this.state.data.course_metrics.map(c => c.name);
                data = this.state.data.course_metrics.map(c => c.fee_due);
            }

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
                        legend: { position: 'bottom' }
                    }
                }
            });
        }

        // Chart 2: Income/Expense Bar Chart
        if (this.branchIncomeChartRef.el) {
            const ctx2 = this.branchIncomeChartRef.el.getContext("2d");
            let labels = [];
            let incomeData = [];
            let expenseData = [];

            if (isManager) {
                labels = this.state.data.branch_metrics.map(b => b.name);
                incomeData = this.state.data.branch_metrics.map(b => b.income);
                expenseData = this.state.data.branch_metrics.map(b => b.expense);
            } else {
                labels = [this.state.data.period_label || 'This Month'];
                incomeData = [this.state.data.income_month];
                expenseData = [this.state.data.expense_month];
            }

            this.incomeChartInstance = new Chart(ctx2, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Income',
                            data: incomeData,
                            backgroundColor: '#1cc88a',
                        },
                        {
                            label: 'Expense',
                            data: expenseData,
                            backgroundColor: '#e74a3b',
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    },
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
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
