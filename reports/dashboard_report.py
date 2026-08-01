from odoo import models, api

class DashboardReport(models.AbstractModel):
    _name = 'report.institute_accounting.report_dashboard'
    _description = 'Dashboard PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        period = data.get('period', 'previous_month') if data else 'previous_month'
        metrics = self.env['institute.accounting.dashboard'].get_metrics(period)
        return {
            'doc_ids': docids,
            'doc_model': 'institute.accounting.dashboard',
            'docs': [],
            'data': metrics,
            'company': self.env.company,
        }
