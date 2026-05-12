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

    @api.model
    def _default_branch_from_accountant(self):
        branch = self.env['student.branch'].search([('accountant_id', '=', self.env.user.id)], limit=1)
        if branch:
            return branch.id
        if hasattr(self.env.user, 'branch_ids') and self.env.user.branch_ids:
            return self.env.user.branch_ids[0].id
        return False

    branch_id = fields.Many2one('student.branch', string='Branch', default=_default_branch_from_accountant)
    
    course_id = fields.Many2one('institute.accounting.course', string='Old Course Group') # Kept for data migration
    course_ids = fields.Many2many(
        'institute.accounting.course', 
        relation='institute_batch_course_rel',
        column1='batch_id',
        column2='course_id',
        string='Course Groups', 
        required=True
    )
    course_variant_id = fields.Many2one('institute.accounting.course.variant', string='Course')
    batch_period = fields.Char(string='Batch Period')
    active = fields.Boolean(default=True)
    student_count = fields.Integer(string='Students', compute='_compute_student_count')

    def init(self):
        super().init()
        # Automatic Data Migration: Migrate old course_id to new course_ids Many2many relation
        self.env.cr.execute("""
            INSERT INTO institute_batch_course_rel (batch_id, course_id)
            SELECT id, course_id FROM institute_accounting_batch 
            WHERE course_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM institute_batch_course_rel rel
                WHERE rel.batch_id = institute_accounting_batch.id 
                AND rel.course_id = institute_accounting_batch.course_id
            );
        """)


    def _compute_student_count(self):
        for record in self:
            record.student_count = self.env['institute.accounting.student'].search_count([('batch_id', '=', record.id)])

    def action_view_students(self):
        self.ensure_one()
        context = {'default_batch_id': self.id}
        if self.course_ids:
            context['default_course_id'] = self.course_ids[0].id
        if self.branch_id:
            context['default_branch_id'] = self.branch_id.id
        return {
            'name': 'Students',
            'type': 'ir.actions.act_window',
            'res_model': 'institute.accounting.student',
            'view_mode': 'tree,form',
            'domain': [('batch_id', '=', self.id)],
            'context': context,
        }

    def action_import_students(self):
        self.ensure_one()
        context = {'default_batch_id': self.id}
        if self.course_ids:
            context['default_course_id'] = self.course_ids[0].id
        if self.branch_id:
            context['default_branch_id'] = self.branch_id.id
        return {
            'name': 'Import Students & Dues',
            'type': 'ir.actions.act_window',
            'res_model': 'institute.accounting.import.student.dues',
            'view_mode': 'form',
            'target': 'new',
            'context': context
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
