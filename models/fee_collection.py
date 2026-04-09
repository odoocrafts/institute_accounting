from odoo import api, fields, models

class StudentFeePaymentInherit(models.Model):
    _inherit = 'student.fee.payment'

    name = fields.Char(string='Receipt Reference', readonly=True, default='New')
    course_id = fields.Many2one('product.product', string='Course')
    batch_id = fields.Many2one('student.batch', string='Batch')
    semester_id = fields.Many2one('institute.semester', string='Semester')
    
    @api.model
    def _default_branch_from_accountant(self):
        branch = self.env['student.branch'].search([('accountant_id', '=', self.env.user.id)], limit=1)
        if branch:
            return branch.id
        if hasattr(self.env.user, 'branch_ids') and self.env.user.branch_ids:
            return self.env.user.branch_ids[0].id
        return False

    # Set as standard field instead of related to allow default auto-selection upon form open
    branch_id = fields.Many2one('student.branch', string='Branch', required=True, default=_default_branch_from_accountant)

    @api.onchange('course_id')
    def _onchange_course(self):
        self.batch_id = False
        self.student_id = False
        if self.course_id:
            return {'domain': {'batch_id': [('course_id', '=', self.course_id.id)]}}

    @api.onchange('batch_id')
    def _onchange_batch(self):
        self.student_id = False
        if self.batch_id:
            return {'domain': {'student_id': [('batch_id', '=', self.batch_id.id)]}}
        elif self.course_id:
            return {'domain': {'student_id': [('course_id', '=', self.course_id.id)]}}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('student.fee.payment') or 'New'
        return super(StudentFeePaymentInherit, self).create(vals_list)

    def action_print_receipt(self):
        for rec in self:
            return self.env.ref('institute_accounting.action_report_fee_receipt').report_action(rec)
