from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class InstituteAccountingTransaction(models.Model):
    _name = 'institute.accounting.transaction'
    _description = 'Institute Accounting Transaction'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    branch_id = fields.Many2one('student.branch', string='Branch', required=True, default=lambda self: self.env.user.branch_ids[:1] if self.env.user.branch_ids else False)
    transaction_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense')
    ], string='Type', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Amount', required=True)
    
    fee_type_id = fields.Many2one('institute.fee.type', string='Fee Type')
    expense_type_id = fields.Many2one('institute.expense.type', string='Expense Type')
    
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI')
    ], string='Payment Method', required=True, default='cash')
    
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    transaction_ref = fields.Char(string='Transaction Reference')
    
    payment_status = fields.Selection([
        ('paid_by_branch', 'Paid by Branch'),
        ('send_to_hq', 'Send to HQ for Payment')
    ], string='Payment Status', default='paid_by_branch')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid')
    ], string='Status', required=True, default='draft', copy=False)
    
    description = fields.Text(string='Description')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('institute.accounting.transaction') or _('New')
        return super(InstituteAccountingTransaction, self).create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Amount must be strictly positive."))

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

    def action_paid(self):
        for rec in self:
            rec.state = 'paid'

    def action_print_voucher(self):
        for rec in self:
            return self.env.ref('institute_accounting.action_report_transaction_voucher').report_action(rec)
