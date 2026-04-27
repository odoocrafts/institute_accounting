from odoo import api, fields, models, _

class UpdateStudentBranchWizard(models.TransientModel):
    _name = 'institute.accounting.update.student.branch'
    _description = 'Update Student Branch'

    branch_id = fields.Many2one('student.branch', string='New Branch', required=True)

    def action_update_branch(self):
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            students = self.env['institute.accounting.student'].browse(active_ids)
            students.write({'branch_id': self.branch_id.id})
        return {'type': 'ir.actions.act_window_close'}
