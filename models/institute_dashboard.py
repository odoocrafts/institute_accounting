from odoo import api, fields, models
from datetime import date

class InstituteDashboard(models.AbstractModel):
    _name = 'institute.accounting.dashboard'
    _description = 'Accounting Dashboard Backend'

    @api.model
    def get_metrics(self, period='previous_month'):
        is_manager = self.env.user.has_group('institute_accounting.group_institute_accounting_manager')
        
        domain_branch = []
        student_domain_branch = []
        if not is_manager:
            # Use sudo() to ensure no access error if branch accountant lacks direct read access to student.branch
            branch = self.env['student.branch'].sudo().search([('accountant_id', '=', self.env.user.id)], limit=1)
            if branch:
                domain_branch = [('branch_id', '=', branch.id)]
                student_domain_branch = [('branch', '=', branch.id)]
            elif hasattr(self.env.user, 'branch_ids') and self.env.user.branch_ids:
                domain_branch = [('branch_id', 'in', self.env.user.branch_ids.ids)]
                student_domain_branch = [('branch', 'in', self.env.user.branch_ids.ids)]
            else:
                domain_branch = [('id', '=', 0)]
                student_domain_branch = [('id', '=', 0)]

        today = date.today()
        
        if period == 'current_month':
            start_date = today.replace(day=1)
            end_date = today
            period_label = "This Month"
        elif period == 'current_fy':
            if today.month >= 4:
                fy_start = today.year
            else:
                fy_start = today.year - 1
            start_date = date(fy_start, 4, 1)
            end_date = date(fy_start + 1, 3, 31)
            period_label = f"FY {fy_start}-{str(fy_start + 1)[-2:]}"
        else:  # default 'previous_month'
            period = 'previous_month'
            first_this_month = today.replace(day=1)
            end_date = first_this_month - timedelta(days=1)
            start_date = end_date.replace(day=1)
            period_label = "Previous Month"
        
        # All paid/refunded transactions in domain_branch
        transactions = self.env['institute.accounting.transaction'].search([('state', 'in', ['paid', 'refunded'])] + domain_branch)

        # 1. Balances up to end_date
        accounts = self.env['institute.account'].search(domain_branch)
        
        def get_account_balance_as_of(acc_id, opening):
            inc = sum(transactions.filtered(lambda t: t.account_id.id == acc_id and t.transaction_type == 'income' and t.date and t.date <= end_date).mapped('amount'))
            exp = sum(transactions.filtered(lambda t: t.account_id.id == acc_id and t.transaction_type == 'expense' and t.date and t.date <= end_date).mapped('amount'))
            return opening + inc - exp

        cash_accounts = accounts.filtered(lambda a: a.account_type == 'cash')
        bank_accounts = accounts.filtered(lambda a: a.account_type in ['bank', 'upi'])
        
        cash_balance = sum(get_account_balance_as_of(a.id, a.opening_balance) for a in cash_accounts)
        bank_balance = sum(get_account_balance_as_of(a.id, a.opening_balance) for a in bank_accounts)
        
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

                b_accounts = self.env['institute.account'].search([('branch_id', '=', b.id)])
                b_cash = sum(get_account_balance_as_of(a.id, a.opening_balance) for a in b_accounts.filtered(lambda a: a.account_type == 'cash'))
                b_bank = sum(get_account_balance_as_of(a.id, a.opening_balance) for a in b_accounts.filtered(lambda a: a.account_type in ['bank', 'upi']))

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
                'cash_balance': sum(b['cash_balance'] for b in branch_metrics),
                'bank_balance': sum(b['bank_balance'] for b in branch_metrics),
                'total_balance': sum(b['total_balance'] for b in branch_metrics),
                'fee_due': sum(b['fee_due'] for b in branch_metrics),
                'income': sum(b['income'] for b in branch_metrics),
                'expense': sum(b['expense'] for b in branch_metrics),
                'profit': sum(b['profit'] for b in branch_metrics),
            }

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
            'currency_symbol': self.env.company.currency_id.symbol or '₹'
        }
