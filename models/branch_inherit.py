from odoo import api, fields, models

class BranchInherit(models.Model):
    _inherit = 'student.branch'

    billing_address = fields.Text(string='Billing Address')
    gstin = fields.Char(string='GSTIN')
    accountant_id = fields.Many2one('res.users', string='Branch Accountant')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    accountant_signature = fields.Image(string='Accountant Signature', max_width=128, max_height=128)

