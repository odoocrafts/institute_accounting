from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class InstituteAccount(models.Model):
    _name = 'institute.account'
    _description = 'Bank / Petty Cash Account'

    name = fields.Char(string='Account Name', required=True)
    branch_id = fields.Many2one('student.branch', string='Branch', required=True)
    account_type = fields.Selection([
        ('cash', 'Petty Cash'),
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
        for rec in self:
            incomes = self.env['institute.accounting.transaction'].search([
                ('account_id', '=', rec.id),
                ('transaction_type', '=', 'income'),
                ('state', 'in', ['paid', 'refunded'])
            ])
            expenses = self.env['institute.accounting.transaction'].search([
                ('account_id', '=', rec.id),
                ('transaction_type', '=', 'expense'),
                ('state', '=', 'paid')
            ])
            rec.current_balance = rec.opening_balance + sum(incomes.mapped('amount')) - sum(expenses.mapped('amount'))

    @api.constrains('branch_id', 'name')
    def _check_unique_name_per_branch(self):
        for rec in self:
            domain = [('name', '=', rec.name), ('branch_id', '=', rec.branch_id.id), ('id', '!=', rec.id)]
            if self.search_count(domain) > 0:
                raise ValidationError(_("An account with this name already exists for this branch!"))

