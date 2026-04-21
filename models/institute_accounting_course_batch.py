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

    @api.onchange('course_variant_id', 'batch_period')
    def _onchange_auto_name(self):
        parts = []
        if self.course_variant_id:
            parts.append(self.course_variant_id.name.upper())
        if self.batch_period:
            parts.append(self.batch_period)
        if parts:
            self.name = ' '.join(parts) + ' BATCH'
