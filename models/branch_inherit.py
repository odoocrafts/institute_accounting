from odoo import api, fields, models

class BranchInherit(models.Model):
    _inherit = 'student.branch'

    billing_address = fields.Text(string='Billing Address')
    gstin = fields.Char(string='GSTIN')
