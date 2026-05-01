from odoo import models, api, _

class PnLReportTemplate(models.AbstractModel):
    _name = 'report.institute_accounting.report_pnl_template'
    _description = 'Profit and Loss Report Template'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        form = data.get('form', {})
        date_from = form.get('date_from')
        date_to = form.get('date_to')
        branch_id = form.get('branch_id')

        domain = [('state', 'in', ['paid', 'refunded'])]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if branch_id:
            domain.append(('branch_id', '=', branch_id))

        transactions = self.env['institute.accounting.transaction'].search(domain)

        # Process Income
        income_transactions = transactions.filtered(lambda t: t.transaction_type == 'income')
        income_dict = {}
        for t in income_transactions:
            category = t.fee_type_id.name if t.fee_type_id else 'Other Income'
            income_dict[category] = income_dict.get(category, 0.0) + t.amount
        
        income_list = [{'category': k, 'amount': v} for k, v in income_dict.items()]
        total_income = sum(income_dict.values())

        # Process Expenses
        expense_transactions = transactions.filtered(lambda t: t.transaction_type == 'expense')
        expense_dict = {}
        for t in expense_transactions:
            category = t.expense_type_id.name if t.expense_type_id else 'Other Expense'
            expense_dict[category] = expense_dict.get(category, 0.0) + t.amount
            
        expense_list = [{'category': k, 'amount': v} for k, v in expense_dict.items()]
        total_expense = sum(expense_dict.values())

        net_profit = total_income - total_expense

        return {
            'doc_ids': docids,
            'doc_model': 'institute.pnl.report.wizard',
            'data': data,
            'date_from': date_from,
            'date_to': date_to,
            'branch_name': form.get('branch_name', 'All Branches'),
            'income_list': sorted(income_list, key=lambda i: i['category']),
            'total_income': total_income,
            'expense_list': sorted(expense_list, key=lambda e: e['category']),
            'total_expense': total_expense,
            'net_profit': net_profit,
            'company': self.env.company,
        }
