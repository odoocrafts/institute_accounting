from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class InstituteAccountingTransaction(models.Model):
    _name = 'institute.accounting.transaction'
    _description = 'Institute Accounting Transaction'
    _order = 'date desc, id desc'

    @api.model
    def _default_branch_from_accountant(self):
        branch = self.env['student.branch'].search([('accountant_id', '=', self.env.user.id)], limit=1)
        if branch:
            return branch.id
        if hasattr(self.env.user, 'branch_ids') and self.env.user.branch_ids:
            return self.env.user.branch_ids[0].id
        return False

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    branch_id = fields.Many2one('student.branch', string='Branch', required=True, default=_default_branch_from_accountant)
    transaction_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense')
    ], string='Type', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Amount', required=True)
    
    fee_type_id = fields.Many2one('institute.fee.type', string='Fee Type')
    expense_type_id = fields.Many2one('institute.expense.type', string='Expense Type')
    paid_to = fields.Char(string='Paid To')
    
    # Fee Collection Fields
    course_id = fields.Many2one('institute.accounting.course', string='Course Group')
    batch_id = fields.Many2one('institute.accounting.batch', string='Batch', domain="[('course_id', '=', course_id)]")
    student_id = fields.Many2one('institute.accounting.student', string='Student', domain="['|', ('batch_id', '=', batch_id), ('course_id', '=', course_id)]")
    
    # We map directly to the semester fee line
    accounting_fee_line_id = fields.Many2one('institute.accounting.student.fee', string='Semester / Fee Line', domain="[('student_id', '=', student_id)]")
    
    student_due = fields.Float(string='Student Due', related='student_id.total_due')
    
    @api.onchange('course_id')
    def _onchange_course(self):
        self.batch_id = False
        self.student_id = False

    @api.onchange('batch_id')
    def _onchange_batch(self):
        self.student_id = False
    
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI')
    ], string='Payment Method', required=True, default='cash')
    
    account_id = fields.Many2one('institute.account', string='Account', domain="[('branch_id', '=', branch_id)]")
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account (Old)')
    transaction_ref = fields.Char(string='Transaction Reference')

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.account_id:
            self.payment_method = self.account_id.account_type
        
    payment_status = fields.Selection([
        ('paid_by_branch', 'Paid by Branch'),
        ('send_to_hq', 'Send to HQ for Payment')
    ], string='Payment Status', default='paid_by_branch')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded')
    ], string='Status', required=True, default='draft', copy=False)
    
    description = fields.Text(string='Description')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('branch_id'):
                vals['branch_id'] = self._default_branch_from_accountant()
            if vals.get('name', _('New')) == _('New'):
                transaction_type = vals.get('transaction_type', 'income')
                branch_id = vals.get('branch_id')
                
                # Dynamic sequence code
                seq_code = f"institute.accounting.{transaction_type}.{branch_id}"
                seq = self.env['ir.sequence'].search([('code', '=', seq_code)], limit=1)
                
                if not seq:
                    branch = self.env['student.branch'].browse(branch_id)
                    seq = self.env['ir.sequence'].sudo().create({
                        'name': f"{transaction_type.capitalize()} Transaction Sequence - Branch {branch.name}",
                        'code': seq_code,
                        'implementation': 'standard',
                        'padding': 4,
                    })
                
                seq_val = seq._next()
                
                if seq_val:
                    if transaction_type == 'income':
                        prefix = self.env['ir.config_parameter'].sudo().get_param('institute_accounting.fee_receipt_prefix', default='JBIA')
                    else:
                        prefix = self.env['ir.config_parameter'].sudo().get_param('institute_accounting.expense_voucher_prefix', default='VOU')
                    
                    date_val = vals.get('date') or fields.Date.context_today(self)
                    if isinstance(date_val, str):
                        date_val = fields.Date.from_string(date_val)
                    year = date_val.year
                    if date_val.month < 4:
                        fin_year = f"{str(year - 1)[-2:]}-{str(year)[-2:]}"
                    else:
                        fin_year = f"{str(year)[-2:]}-{str(year + 1)[-2:]}"
                    
                    # Remove any existing prefix letters if the sequence somehow still has INS/ACC/
                    import re
                    number_part = re.sub(r'[^0-9]', '', seq_val)
                    if not number_part:
                        number_part = seq_val
                    
                    vals['name'] = f"{prefix}/{number_part}/{fin_year}"
                else:
                    vals['name'] = _('New')
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
            if rec.transaction_type == 'income' and rec.student_id and rec.accounting_fee_line_id:
                # Deduct from the specific accounting fee line
                rec.accounting_fee_line_id.paid_amount += rec.amount


    def action_print_voucher(self):
        for rec in self:
            return self.env.ref('institute_accounting.action_report_transaction_voucher').report_action(rec)

    def action_print_receipt(self):
        for rec in self:
            return self.env.ref('institute_accounting.action_report_fee_receipt').report_action(rec)

    def action_refund(self):
        for rec in self:
            if rec.transaction_type != 'income' or rec.state != 'paid':
                continue
            return {
                'name': _('Refund Fee'),
                'type': 'ir.actions.act_window',
                'res_model': 'institute.accounting.refund.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_transaction_id': rec.id,
                    'default_amount': rec.amount,
                    'default_account_id': rec.account_id.id,
                    'default_payment_method': rec.payment_method,
                }
            }
