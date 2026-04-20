from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fee_receipt_prefix = fields.Char(
        string='Fee Receipt Prefix',
        config_parameter='institute_accounting.fee_receipt_prefix',
        default='JBIA',
        help="Global prefix for the fee receipts (e.g. JBIA)"
    )
