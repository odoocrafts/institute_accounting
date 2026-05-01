from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PnLReportWizard(models.TransientModel):
    _name = 'institute.pnl.report.wizard'
    _description = 'Profit and Loss Report Wizard'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    @api.model
    def _default_branch_id(self):
        # Default to branch accountant's branch if they are not a manager
        if not self.env.user.has_group('institute_accounting.group_institute_accounting_manager'):
            branch = self.env['student.branch'].search([('accountant_id', '=', self.env.user.id)], limit=1)
            if branch:
                return branch.id
            if hasattr(self.env.user, 'branch_ids') and self.env.user.branch_ids:
                return self.env.user.branch_ids[0].id
        return False

    branch_id = fields.Many2one('student.branch', string='Branch', default=_default_branch_id)
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(_('The Start Date must be before the End Date.'))

    def action_generate_report(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'branch_id': self.branch_id.id if self.branch_id else False,
                'branch_name': self.branch_id.name if self.branch_id else 'All Branches',
            },
        }
        return self.env.ref('institute_accounting.action_report_pnl').report_action(self, data=data)
