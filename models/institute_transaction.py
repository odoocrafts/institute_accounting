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
            return branch
        return self.env.user.branch_ids[:1] if hasattr(self.env.user, 'branch_ids') and self.env.user.branch_ids else False

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
    
    # Fee Collection Fields
    course_id = fields.Many2one('product.product', string='Course')
    batch_id = fields.Many2one('student.batch', string='Batch', domain="[('course_id', '=', course_id)]")
    student_id = fields.Many2one('student.student', string='Student', domain="['|', ('batch_id', '=', batch_id), ('course_id', '=', course_id)]")
    semester_id = fields.Many2one('institute.semester', string='Semester')
    student_due = fields.Float(string='Student Due', related='student_id.computed_due')
    
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
            if rec.transaction_type == 'income' and rec.student_id:
                # Create a student fee payment
                self.env['student.fee.payment'].create({
                    'name': rec.name,
                    'student_id': rec.student_id.id,
                    'payment_date': rec.date,
                    'amount': rec.amount,
                    'payment_method': rec.payment_method,
                    'reference': rec.transaction_ref,
                    'course_id': rec.course_id.id if rec.course_id else False,
                    'batch_id': rec.batch_id.id if rec.batch_id else False,
                    'semester_id': rec.semester_id.id if rec.semester_id else False,
                })

    def action_print_voucher(self):
        for rec in self:
            return self.env.ref('institute_accounting.action_report_transaction_voucher').report_action(rec)

    def action_print_receipt(self):
        for rec in self:
            # We can print the same fee receipt template using this transaction record since it has all fields.
            # But the report is bound to student.fee.payment!
            # Let's find the created student.fee.payment record and print that, or we can just bind a new report to transaction later.
            payment = self.env['student.fee.payment'].search([('name', '=', rec.name)], limit=1)
            if payment:
                return self.env.ref('institute_accounting.action_report_fee_receipt').report_action(payment)
            return True
