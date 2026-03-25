from odoo import models, fields, tools

class InstituteAccountingReport(models.Model):
    _name = 'institute.accounting.report'
    _description = 'Institute Accounting Report'
    _auto = False

    name = fields.Char('Reference', readonly=True)
    date = fields.Date('Date', readonly=True)
    branch_id = fields.Many2one('student.branch', string='Branch', readonly=True)
    transaction_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense')
    ], string='Type', readonly=True)
    amount = fields.Float('Amount', readonly=True)
    net_amount = fields.Float('Net Amount (P&L)', readonly=True)
    fee_type_id = fields.Many2one('institute.fee.type', string='Fee Type', readonly=True)
    expense_type_id = fields.Many2one('institute.expense.type', string='Expense Type', readonly=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI')
    ], string='Payment Method', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid')
    ], string='Status', readonly=True)

    def _select(self):
        return """
            SELECT
                t.id,
                t.name,
                t.date,
                t.branch_id,
                t.transaction_type,
                t.amount,
                CASE
                    WHEN t.transaction_type = 'income' THEN t.amount
                    ELSE -t.amount
                END as net_amount,
                t.fee_type_id,
                t.expense_type_id,
                t.payment_method,
                t.state
        """

    def _from(self):
        return """
            FROM institute_accounting_transaction t
        """

    def _where(self):
        return """
            WHERE t.state != 'draft'
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            %s
            %s
        )""" % (self._table, self._select(), self._from(), self._where()))
