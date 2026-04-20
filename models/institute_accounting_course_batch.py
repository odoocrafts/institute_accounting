from odoo import api, fields, models

class InstituteAccountingCourse(models.Model):
    _name = 'institute.accounting.course'
    _description = 'Accounting Course'
    
    name = fields.Char(string='Course Name', required=True)
    active = fields.Boolean(default=True)

class InstituteAccountingBatch(models.Model):
    _name = 'institute.accounting.batch'
    _description = 'Accounting Batch'
    
    name = fields.Char(string='Batch Name', required=True)
    course_id = fields.Many2one('institute.accounting.course', string='Course', required=True)
    batch_period = fields.Char(string='Batch Period')
    active = fields.Boolean(default=True)
