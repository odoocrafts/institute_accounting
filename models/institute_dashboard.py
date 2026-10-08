from odoo import api, fields, models
from datetime import date, timedelta

class InstituteDashboard(models.AbstractModel):
    _name = 'institute.accounting.dashboard'
    _description = 'Accounting Dashboard Backend'

    @api.model
    def get_metrics(self, period='current_month'):
        is_manager = self.env.user.has_group('institute_accounting.group_institute_accounting_manager')
        
        domain_branch = []
        visible_branch_ids = None
        if not is_manager:
            # Include every branch this accountant owns, plus any extra branches
            # granted on the user. A single limit=1 match used to drop the rest,
            # so their cash never appeared on the dashboard.
            branch_ids = set(self.env['student.branch'].sudo().search([
                ('accountant_id', '=', self.env.user.id),
            ]).ids)
            allowed_branches = self.env.user.sudo().branch_ids
            if allowed_branches:
                branch_ids.update(allowed_branches.ids)
            visible_branch_ids = list(branch_ids)
            if visible_branch_ids:
                domain_branch = [('branch_id', 'in', visible_branch_ids)]
            else:
                domain_branch = [('id', '=', 0)]
                visible_branch_ids = []

        today = date.today()
        
        if period == 'previous_month':
            first_this_month = today.replace(day=1)
            end_date = first_this_month - timedelta(days=1)
            start_date = end_date.replace(day=1)
            period_label = start_date.strftime("%B %Y")
        elif period == 'current_fy':
            if today.month >= 4:
                fy_start = today.year
            else:
                fy_start = today.year - 1
            start_date = date(fy_start, 4, 1)
            end_date = date(fy_start + 1, 3, 31)
            period_label = f"FY {fy_start}-{str(fy_start + 1)[-2:]}"
        else:  # default 'current_month'
            period = 'current_month'
            start_date = today.replace(day=1)
            end_date = today
            period_label = start_date.strftime("%B %Y")
        
        # All paid/refunded transactions in domain_branch
        transactions = self.env['institute.accounting.transaction'].search([('state', 'in', ['paid', 'refunded'])] + domain_branch)

        # 1. Live cash / bank balances. These follow institute.account.current_balance
        # (opening + every settled receipt and expense), not the selected period.
        # The period filter only applies to income, expense, and profit below.
        accounts = self.env['institute.account'].search(domain_branch)
        accounts.mapped('current_balance')
        currency = self.env.company.currency_id

        def _round(value):
            return currency.round(value) if currency else value

        def _split_balances(account_records):
            cash = sum(account.current_balance for account in account_records if account.account_type == 'cash')
            bank = sum(account.current_balance for account in account_records if account.account_type in ('bank', 'upi'))
            return cash, bank

        cash_balance, bank_balance = _split_balances(accounts)
        unassigned = self.env['institute.accounting.transaction']._unassigned_liquid_balances(visible_branch_ids)
        cash_balance += sum(amounts['cash'] for amounts in unassigned.values())
        bank_balance += sum(amounts['bank'] for amounts in unassigned.values())
        cash_balance = _round(cash_balance)
        bank_balance = _round(bank_balance)
        
        # 2. Fee Due
        students = self.env['institute.accounting.student'].search(domain_branch)
        fee_due = sum(students.mapped('total_due'))

        # 3. Income / Expenses for selected period
        period_trans = transactions.filtered(lambda t: t.date and start_date <= t.date <= end_date)
        income_month = sum(period_trans.filtered(lambda t: t.transaction_type in ('income', 'other_income')).mapped('amount'))
        expense_month = sum(period_trans.filtered(lambda t: t.transaction_type == 'expense').mapped('amount'))
        
        income_today = sum(transactions.filtered(lambda t: t.transaction_type in ('income', 'other_income') and t.date == today).mapped('amount'))
        expense_today = sum(transactions.filtered(lambda t: t.transaction_type == 'expense' and t.date == today).mapped('amount'))
        
        # 4. Top Expenses for selected period
        expenses = period_trans.filtered(lambda t: t.transaction_type == 'expense')
        expense_dict = {}
        for exp in expenses:
            cat_name = exp.expense_type_id.name or 'Other'
            expense_dict[cat_name] = expense_dict.get(cat_name, 0) + exp.amount
            
        top_expenses = [{'category': k, 'amount': v} for k, v in sorted(expense_dict.items(), key=lambda item: item[1], reverse=True)[:5]]

        # 5. Branch Metrics (Manager only)
        branch_metrics = []
        branch_totals = {
            'cash_balance': 0.0,
            'bank_balance': 0.0,
            'total_balance': 0.0,
            'fee_due': 0.0,
            'income': 0.0,
            'expense': 0.0,
            'profit': 0.0,
        }
        if is_manager:
            branches = self.env['student.branch'].sudo().search([])
            for b in branches:
                b_trans = period_trans.filtered(lambda t: t.branch_id.id == b.id)
                inc = sum(b_trans.filtered(lambda t: t.transaction_type in ('income', 'other_income')).mapped('amount'))
                exp = sum(b_trans.filtered(lambda t: t.transaction_type == 'expense').mapped('amount'))
                
                b_students = self.env['institute.accounting.student'].search([('branch_id', '=', b.id)])
                b_fee_due = sum(b_students.mapped('total_due'))

                b_accounts = accounts.filtered(lambda account, branch_id=b.id: account.branch_id.id == branch_id)
                b_cash, b_bank = _split_balances(b_accounts)
                extra = unassigned.get(b.id, {})
                b_cash = _round(b_cash + extra.get('cash', 0.0))
                b_bank = _round(b_bank + extra.get('bank', 0.0))

                branch_metrics.append({
                    'id': b.id,
                    'name': b.name,
                    'cash_balance': b_cash,
                    'bank_balance': b_bank,
                    'total_balance': b_cash + b_bank,
                    'income': inc,
                    'expense': exp,
                    'profit': inc - exp,
                    'fee_due': b_fee_due
                })

            branch_totals = {
                'cash_balance': _round(sum(b['cash_balance'] for b in branch_metrics)),
                'bank_balance': _round(sum(b['bank_balance'] for b in branch_metrics)),
                'total_balance': _round(sum(b['total_balance'] for b in branch_metrics)),
                'fee_due': sum(b['fee_due'] for b in branch_metrics),
                'income': sum(b['income'] for b in branch_metrics),
                'expense': sum(b['expense'] for b in branch_metrics),
                'profit': sum(b['profit'] for b in branch_metrics),
            }
            covered_branch_ids = set(branches.ids)
            loose_cash, loose_bank = _split_balances(accounts.filtered(
                lambda account: account.branch_id.id not in covered_branch_ids
            ))
            extra_cash = sum(amounts['cash'] for branch_id, amounts in unassigned.items() if branch_id not in covered_branch_ids)
            extra_bank = sum(amounts['bank'] for branch_id, amounts in unassigned.items() if branch_id not in covered_branch_ids)
            cash_balance = _round(branch_totals['cash_balance'] + loose_cash + extra_cash)
            bank_balance = _round(branch_totals['bank_balance'] + loose_bank + extra_bank)

        # 6. Course Metrics (Branch Accountant only)
        course_metrics = []
        if not is_manager:
            courses = self.env['institute.accounting.course'].sudo().search([])
            for c in courses:
                c_students = students.filtered(lambda s: s.course_id.id == c.id)
                c_fee_due = sum(c_students.mapped('total_due'))
                if c_fee_due > 0:
                    course_metrics.append({
                        'name': c.name,
                        'fee_due': c_fee_due
                    })
        
        # 7. Generate Chart URLs for PDF Report
        import urllib.parse
        import json
        
        pie_chart_url = ""
        bar_chart_url = ""
        
        if is_manager and branch_metrics:
            pie_labels = [b['name'][:15] + '..' if len(b['name']) > 15 else b['name'] for b in branch_metrics]
            pie_data = [b['fee_due'] for b in branch_metrics]
            pie_config = {
                'type': 'pie',
                'data': {
                    'labels': pie_labels,
                    'datasets': [{'data': pie_data, 'backgroundColor': ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#5a5c69', '#2e59d9', '#17a673', '#2c9faf']}]
                },
                'options': {
                    'plugins': {
                        'legend': {'position': 'bottom'},
                        'datalabels': {'display': False}
                    }
                }
            }
            pie_chart_url = f"https://quickchart.io/chart?w=500&h=300&c={urllib.parse.quote(json.dumps(pie_config))}"
            
            bar_labels = pie_labels
            bar_income = [b['income'] for b in branch_metrics]
            bar_expense = [b['expense'] for b in branch_metrics]
            bar_config = {
                'type': 'bar',
                'data': {
                    'labels': bar_labels,
                    'datasets': [
                        {'label': 'Income', 'data': bar_income, 'backgroundColor': '#1cc88a'},
                        {'label': 'Expense', 'data': bar_expense, 'backgroundColor': '#e74a3b'}
                    ]
                },
                'options': {'plugins': {'legend': {'position': 'bottom'}}}
            }
            bar_chart_url = f"https://quickchart.io/chart?w=500&h=300&c={urllib.parse.quote(json.dumps(bar_config))}"

        return {
            'is_manager': is_manager,
            'period': period,
            'period_label': period_label,
            'cash_balance': cash_balance,
            'bank_balance': bank_balance,
            'fee_due': fee_due,
            'income_month': income_month,
            'expense_month': expense_month,
            'income_today': income_today,
            'expense_today': expense_today,
            'top_expenses': top_expenses,
            'branch_metrics': branch_metrics,
            'branch_totals': branch_totals,
            'course_metrics': course_metrics,
            'pie_chart_url': pie_chart_url,
            'bar_chart_url': bar_chart_url,
            'currency_symbol': self.env.company.currency_id.symbol or '₹'
        }
