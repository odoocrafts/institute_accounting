from odoo import models, fields

class InstituteFeeType(models.Model):
    _name = 'institute.fee.type'
    _description = 'Fee Type'

    name = fields.Char(string='Fee Type Name', required=True)
    active = fields.Boolean(default=True)

class InstituteExpenseType(models.Model):
    _name = 'institute.expense.type'
    _description = 'Expense Type'

    name = fields.Char(string='Expense Type Name', required=True)
    active = fields.Boolean(default=True)
