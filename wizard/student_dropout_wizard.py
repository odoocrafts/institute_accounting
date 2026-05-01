from odoo import models, fields, _

class StudentDropoutWizard(models.TransientModel):
    _name = 'institute.accounting.student.dropout.wizard'
    _description = 'Student Dropout Wizard'

    student_id = fields.Many2one('institute.accounting.student', string='Student', required=True)
    reason = fields.Text(string='Reason for Dropout', required=True)

    def action_confirm(self):
        self.ensure_one()
        # Post a message in the chatter
        self.student_id.message_post(body=_("Student marked as dropped out. Reason: %s", self.reason))
        # Set dropout reason and archive student
        self.student_id.write({
            'dropout_reason': self.reason,
            'active': False,
        })
        return {'type': 'ir.actions.act_window_close'}
