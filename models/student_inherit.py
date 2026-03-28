from odoo import api, fields, models

class StudentInherit(models.Model):
    _inherit = 'student.student'

    current_semester_id = fields.Many2one('institute.semester', string='Current Semester')
    opening_balance = fields.Float(string='Opening Balance (Due)', default=0.0)
    computed_due = fields.Float(string='Computed Due', compute='_compute_student_due', store=True)

    @api.depends('current_semester_id', 'total_fee', 'semester_count', 'opening_balance', 'paid_amount', 'current_semester_id.sequence')
    def _compute_student_due(self):
        for student in self:
            sem_fee = 0.0
            if student.semester_count and student.total_fee:
                sem_fee = student.total_fee / student.semester_count
            
            # calculate how many semesters to charge for this student
            current_sem_seq = student.current_semester_id.sequence if student.current_semester_id else 0
            # limit the sequence up to the maximum semesters
            if current_sem_seq > student.semester_count:
                current_sem_seq = student.semester_count
                
            total_charged = (current_sem_seq * sem_fee) + student.opening_balance
            student.computed_due = total_charged - student.paid_amount
