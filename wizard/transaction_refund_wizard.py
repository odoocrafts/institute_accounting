from odoo import api, fields, models, _

class TransactionRefundWizard(models.TransientModel):
    _name = 'institute.accounting.refund.wizard'
    _description = 'Fee Refund Wizard'

    transaction_id = fields.Many2one('institute.accounting.transaction', string='Original Transaction', required=True, readonly=True)
    amount = fields.Float(string='Refund Amount', required=True, readonly=True)
    
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI')
    ], string='Refund Method', required=True, default='cash')
    
    account_id = fields.Many2one('institute.account', string='Account', required=True)
    reason = fields.Char(string='Reason for Refund', required=True)

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.account_id:
            self.payment_method = self.account_id.account_type

    def action_confirm_refund(self):
        self.ensure_one()
        
        # 1. Reverse the fee from the student's dues
        if self.transaction_id.accounting_fee_line_id:
            self.transaction_id.accounting_fee_line_id.paid_amount -= self.transaction_id.amount
            
        # 2. Change original transaction to 'refunded'
        self.transaction_id.state = 'refunded'
        
        # 3. Add reason to original record description
        msg = f"Reverted fee and initiated refund via {self.payment_method.capitalize()}. Reason: {self.reason}"
        if self.transaction_id.description:
            self.transaction_id.description = f"{self.transaction_id.description}\n\n[REFUND NOTE]: {msg}"
        else:
            self.transaction_id.description = f"[REFUND NOTE]: {msg}"
        
        # 4. Find or create Refund Expense Type
        expense_type = self.env['institute.expense.type'].search([('name', '=', 'Fee Refund')], limit=1)
        if not expense_type:
            expense_type = self.env['institute.expense.type'].create({'name': 'Fee Refund', 'active': True})
            
        # 5. Create new expense transaction for the money going out
        new_expense = self.env['institute.accounting.transaction'].create({
            'transaction_type': 'expense',
            'state': 'paid',
            'amount': self.amount,
            'payment_method': self.payment_method,
            'account_id': self.account_id.id,
            'branch_id': self.transaction_id.branch_id.id,
            'date': fields.Date.context_today(self),
            'expense_type_id': expense_type.id,
            'paid_to': self.transaction_id.student_id.name if self.transaction_id.student_id else 'Student',
            'transaction_ref': f'Refund of {self.transaction_id.name}',
            'description': self.reason
        })
        
        return {'type': 'ir.actions.act_window_close'}
