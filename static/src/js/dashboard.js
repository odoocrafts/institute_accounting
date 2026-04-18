/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class AccountingDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
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
            await this.fetchData();
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
