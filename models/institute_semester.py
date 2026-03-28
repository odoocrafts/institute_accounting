from odoo import api, fields, models

class InstituteSemester(models.Model):
    _name = 'institute.semester'
    _description = 'Semester Master'
    
    name = fields.Char(string='Semester Name', required=True)
    sequence = fields.Integer(string='Sequence Number', required=True, default=1, help='Used for calculations, e.g. 1, 2, 3')
    active = fields.Boolean(default=True)
