from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class InstituteAccount(models.Model):
    _name = 'institute.account'
    _description = 'Bank / Petty Cash Account'

    name = fields.Char(string='Account Name', required=True)
    branch_id = fields.Many2one('student.branch', string='Branch', required=True)
    account_type = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Account'),
        ('upi', 'UPI')
    ], string='Type', required=True, default='cash')
    
    account_number = fields.Char(string='Account Number / UPI ID')
    bank_name = fields.Char(string='Bank Name')
    opening_balance = fields.Float(string='Opening Balance', default=0.0)
    current_balance = fields.Float(string='Current Balance', compute='_compute_current_balance', store=False)
    active = fields.Boolean(default=True)

    @api.depends('opening_balance')
    def _compute_current_balance(self):
        """Live balance: opening + settled receipts (including other income) - paid expenses.

        Refunded receipts stay in the inflow because the refund is posted as its own
        paid expense. Every settled transaction on the account is included, with no
        period cutoff, so dashboards and reports can reuse this figure.
        """
        totals = {rec.id: 0.0 for rec in self}
        stored = self.filtered(lambda rec: isinstance(rec.id, int))
        if stored:
            rows = self.env['institute.accounting.transaction']._read_group(
                [('account_id', 'in', stored.ids), ('state', 'in', ['paid', 'refunded'])],
                groupby=['account_id', 'transaction_type', 'state'],
                aggregates=['amount:sum'],
            )
            for account, transaction_type, state, amount in rows:
                if not account:
                    continue
                amount = amount or 0.0
                if transaction_type in ('income', 'other_income') and state in ('paid', 'refunded'):
                    totals[account.id] += amount
                elif transaction_type == 'expense' and state == 'paid':
                    totals[account.id] -= amount

        currency = self.env.company.currency_id
        for rec in self:
            balance = rec.opening_balance + totals.get(rec.id, 0.0)
            rec.current_balance = currency.round(balance) if currency else balance

    @api.constrains('branch_id', 'name')
    def _check_unique_name_per_branch(self):
        for rec in self:
            domain = [('name', '=', rec.name), ('branch_id', '=', rec.branch_id.id), ('id', '!=', rec.id)]
            if self.search_count(domain) > 0:
                raise ValidationError(_("An account with this name already exists for this branch!"))

