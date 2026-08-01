from odoo import api, fields, models
from datetime import date

class InstituteDashboard(models.AbstractModel):
    _name = 'institute.accounting.dashboard'
    _description = 'Accounting Dashboard Backend'

    @api.model
    def get_metrics(self):
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
        first_day_month = today.replace(day=1)
        
        # 1. Balances
        accounts = self.env['institute.account'].search(domain_branch)
        cash_balance = sum(accounts.filtered(lambda a: a.account_type == 'cash').mapped('current_balance'))
        bank_balance = sum(accounts.filtered(lambda a: a.account_type in ['bank', 'upi']).mapped('current_balance'))
        
        # 2. Fee Due
        students = self.env['institute.accounting.student'].search(domain_branch)
        fee_due = sum(students.mapped('total_due'))

        # 3. Income / Expenses
        transactions = self.env['institute.accounting.transaction'].search([('state', 'in', ['paid', 'refunded'])] + domain_branch)
        
        income_month = sum(transactions.filtered(lambda t: t.transaction_type in ('income', 'other_income') and t.date and t.date >= first_day_month).mapped('amount'))
        expense_month = sum(transactions.filtered(lambda t: t.transaction_type == 'expense' and t.date and t.date >= first_day_month).mapped('amount'))
        
        income_today = sum(transactions.filtered(lambda t: t.transaction_type in ('income', 'other_income') and t.date == today).mapped('amount'))
        expense_today = sum(transactions.filtered(lambda t: t.transaction_type == 'expense' and t.date == today).mapped('amount'))
        
        # 4. Top Expenses
        expenses = transactions.filtered(lambda t: t.transaction_type == 'expense' and t.date and t.date >= first_day_month)
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
                b_trans = transactions.filtered(lambda t: t.branch_id.id == b.id and t.date and t.date >= first_day_month)
                inc = sum(b_trans.filtered(lambda t: t.transaction_type in ('income', 'other_income')).mapped('amount'))
                exp = sum(b_trans.filtered(lambda t: t.transaction_type == 'expense').mapped('amount'))
                
                b_students = self.env['institute.accounting.student'].search([('branch_id', '=', b.id)])
                b_fee_due = sum(b_students.mapped('total_due'))

                b_accounts = self.env['institute.account'].search([('branch_id', '=', b.id)])
                b_cash = sum(b_accounts.filtered(lambda a: a.account_type == 'cash').mapped('current_balance'))
                b_bank = sum(b_accounts.filtered(lambda a: a.account_type in ['bank', 'upi']).mapped('current_balance'))

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
