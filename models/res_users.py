from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    branch_ids = fields.Many2many(
        'student.branch',
        'res_users_student_branch_rel',
        'user_id',
        'branch_id',
        string='Allowed Branches'
    )
