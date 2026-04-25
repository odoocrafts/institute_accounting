from odoo import api, fields, models

class InstituteAccountingCourse(models.Model):
    _name = 'institute.accounting.course'
    _description = 'Accounting Course Group'
    
    name = fields.Char(string='Course Group Name', required=True)
    active = fields.Boolean(default=True)

class InstituteAccountingCourseVariant(models.Model):
    _name = 'institute.accounting.course.variant'
    _description = 'Accounting Course'

    name = fields.Char(string='Course Name', required=True)
    active = fields.Boolean(default=True)

class InstituteAccountingBatch(models.Model):
    _name = 'institute.accounting.batch'
    _description = 'Accounting Batch'
    
    name = fields.Char(string='Batch Name', required=True)
    course_id = fields.Many2one('institute.accounting.course', string='Course Group', required=True)
    course_variant_id = fields.Many2one('institute.accounting.course.variant', string='Course')
    batch_period = fields.Char(string='Batch Period')
    active = fields.Boolean(default=True)
    student_count = fields.Integer(string='Students', compute='_compute_student_count')

    def _compute_student_count(self):
        for record in self:
            record.student_count = self.env['institute.accounting.student'].search_count([('batch_id', '=', record.id)])

    def action_view_students(self):
        self.ensure_one()
        return {
            'name': 'Students',
            'type': 'ir.actions.act_window',
            'res_model': 'institute.accounting.student',
            'view_mode': 'tree,form',
            'domain': [('batch_id', '=', self.id)],
            'context': {'default_batch_id': self.id, 'default_course_id': self.course_id.id},
        }

    def action_import_students(self):
        self.ensure_one()
        return {
            'name': 'Import Students & Dues',
            'type': 'ir.actions.act_window',
            'res_model': 'institute.accounting.import.student.dues',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_course_id': self.course_id.id,
                'default_batch_id': self.id,
            }
        }

    @api.onchange('course_variant_id', 'batch_period')
    def _onchange_auto_name(self):
        parts = []
        if self.course_variant_id:
            parts.append(self.course_variant_id.name.upper())
        if self.batch_period:
            parts.append(self.batch_period)
        if parts:
            self.name = ' '.join(parts) + ' BATCH'
