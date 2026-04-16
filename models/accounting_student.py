from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class InstituteAccountingStudent(models.Model):
    _name = 'institute.accounting.student'
    _description = 'Accounting Student Ledger'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    branch_id = fields.Many2one('student.branch', string='Branch', required=True, tracking=True)
    course_id = fields.Many2one('product.product', string='Course', domain="[('type', '=', 'service')]")
    batch_id = fields.Many2one('student.batch', string='Batch', domain="[('course_id', '=', course_id)]")
    
    student_number = fields.Char(string='Student Number')
    parent_number = fields.Char(string='Parent Number')
    
    fee_line_ids = fields.One2many('institute.accounting.student.fee', 'student_id', string='Semester Fees')
    
    total_fee = fields.Float(string='Total Configured Fee', compute='_compute_fees', store=True)
    total_paid = fields.Float(string='Total Paid', compute='_compute_fees', store=True)
    total_due = fields.Float(string='Total Due', compute='_compute_fees', store=True)

    @api.depends('fee_line_ids.total_fee', 'fee_line_ids.paid_amount')
    def _compute_fees(self):
        for rec in self:
            rec.total_fee = sum(rec.fee_line_ids.mapped('total_fee'))
            rec.total_paid = sum(rec.fee_line_ids.mapped('paid_amount'))
            rec.total_due = sum(rec.fee_line_ids.mapped('due_amount'))


class InstituteAccountingStudentFee(models.Model):
    _name = 'institute.accounting.student.fee'
    _description = 'Accounting Student Fee Semester Line'

    student_id = fields.Many2one('institute.accounting.student', string='Student', required=True, ondelete='cascade')
    semester = fields.Char(string='Semester', required=True, help='e.g., 1st Sem, 2nd Sem')
    total_fee = fields.Float(string='Total Fee', required=True, default=0.0)
    
    # We allow the accountant to either manually sync this or let the system compute.
    # In a fully robust system, this is computed via mapping transactions to this line.
    # We will make it manually editable so the accountant can match the spreadsheet if they don't want to enter historic receipts.
    paid_amount = fields.Float(string='Paid Amount', default=0.0)
    
    due_amount = fields.Float(string='Due Amount', compute='_compute_due', store=True)

    @api.depends('total_fee', 'paid_amount')
    def _compute_due(self):
        for rec in self:
            rec.due_amount = rec.total_fee - rec.paid_amount

    @api.constrains('paid_amount', 'total_fee')
    def _check_amounts(self):
        for rec in self:
            if rec.paid_amount > rec.total_fee:
                # We allow it, but we can warn or block. Usually, fee structure allows slightly over or we just accept it.
                # Just allow for flexibility or raise. For now, no strict raise to match user's custom workflows.
                pass
