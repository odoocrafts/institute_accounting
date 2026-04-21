from odoo import api, fields, models

class BranchInherit(models.Model):
    _inherit = 'student.branch'

    billing_address = fields.Text(string='Billing Address')
    gstin = fields.Char(string='GSTIN')
    accountant_id = fields.Many2one('res.users', string='Branch Accountant')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    accountant_signature = fields.Image(string='Accountant Signature', max_width=512, max_height=512)
    signature_text = fields.Html(string='Signature Details', sanitize=True, help="Editable text displayed under the signature image on receipts")
    round_seal = fields.Image(string='Round Seal', max_width=512, max_height=512)
    non_refundable_seal = fields.Image(string='Fees Not Refundable Seal', max_width=512, max_height=512)
