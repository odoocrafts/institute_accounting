from odoo import api, fields, models, _

class TransactionEditWizard(models.TransientModel):
    _name = 'institute.accounting.edit.wizard'
    _description = 'Edit Transaction Wizard'

    transaction_id = fields.Many2one('institute.accounting.transaction', string='Transaction', required=True, readonly=True)
    
    amount = fields.Float(string='Amount', required=True)
    date = fields.Date(string='Date', required=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI')
    ], string='Payment Method', required=True)
    
    account_id = fields.Many2one('institute.account', string='Account', required=True)
    transaction_ref = fields.Char(string='Transaction Reference')
    edit_reason = fields.Char(string='Edit Reason', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(TransactionEditWizard, self).default_get(fields_list)
        transaction_id = self.env.context.get('default_transaction_id')
        if transaction_id:
            transaction = self.env['institute.accounting.transaction'].browse(transaction_id)
            res.update({
                'transaction_id': transaction.id,
                'amount': transaction.amount,
                'date': transaction.date,
                'payment_method': transaction.payment_method,
                'account_id': transaction.account_id.id,
                'transaction_ref': transaction.transaction_ref,
            })
        return res

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.account_id:
            self.payment_method = self.account_id.account_type

    def action_confirm_edit(self):
        self.ensure_one()
        
        changes = []
        if self.transaction_id.amount != self.amount:
            changes.append(f"Amount: {self.transaction_id.amount} -> {self.amount}")
            if self.transaction_id.transaction_type in ('income', 'other_income') and self.transaction_id.accounting_fee_line_id:
                self.transaction_id.accounting_fee_line_id.paid_amount -= self.transaction_id.amount
                self.transaction_id.accounting_fee_line_id.paid_amount += self.amount

        if self.transaction_id.date != self.date:
            changes.append(f"Date: {self.transaction_id.date} -> {self.date}")
        if self.transaction_id.payment_method != self.payment_method:
            changes.append(f"Payment Method: {self.transaction_id.payment_method} -> {self.payment_method}")
        if self.transaction_id.account_id.id != self.account_id.id:
            changes.append(f"Account: {self.transaction_id.account_id.name} -> {self.account_id.name}")
        if self.transaction_id.transaction_ref != self.transaction_ref:
            changes.append(f"Transaction Ref: {self.transaction_id.transaction_ref} -> {self.transaction_ref}")
            
        if not changes:
            return {'type': 'ir.actions.act_window_close'}
            
        # Update the transaction
        self.transaction_id.write({
            'amount': self.amount,
            'date': self.date,
            'payment_method': self.payment_method,
            'account_id': self.account_id.id,
            'transaction_ref': self.transaction_ref,
        })
        
        # Log the changes
        change_log = "\n".join(changes)
        msg = f"[EDIT LOG]:\n{change_log}\nReason: {self.edit_reason}"
        if self.transaction_id.description:
            self.transaction_id.description = f"{self.transaction_id.description}\n\n{msg}"
        else:
            self.transaction_id.description = msg
            
        return {'type': 'ir.actions.act_window_close'}
