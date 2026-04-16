from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import io
import re

try:
    import openpyxl
except ImportError:
    openpyxl = None

class ImportStudentDuesWizard(models.TransientModel):
    _name = 'institute.accounting.import.student.dues'
    _description = 'Import Student Dues Wizard'

    branch_id = fields.Many2one('student.branch', string='Branch', required=True)
    course_id = fields.Many2one('institute.accounting.course', string='Course', required=True)
    batch_id = fields.Many2one('institute.accounting.batch', string='Batch', required=True, domain="[('course_id', '=', course_id)]")
    
    file = fields.Binary('Excel File', required=True)
    file_name = fields.Char('File Name')

    def action_import(self):
        if not self.file:
            raise UserError(_("Please upload an Excel file."))

        file_content = base64.b64decode(self.file)
        all_rows = []
        try:
            if not openpyxl:
                raise ImportError("openpyxl missing")
            workbook = openpyxl.load_workbook(filename=io.BytesIO(file_content), data_only=True)
            sheet = workbook.active
            for row in sheet.iter_rows(values_only=True):
                all_rows.append(list(row))
        except Exception as e:
            try:
                import xlrd
                workbook = xlrd.open_workbook(file_contents=file_content)
                sheet = workbook.sheet_by_index(0)
                for rx in range(sheet.nrows):
                    all_rows.append(sheet.row_values(rx))
            except ImportError:
                raise UserError(_("Error reading file: %s. (Make sure you are uploading a valid .xlsx file or install xlrd for .xls support)") % str(e))
            except Exception as inner_e:
                raise UserError(_("Error reading file. The file might be corrupted or in an unsupported format. %s") % str(inner_e))

        if not all_rows:
            raise UserError(_("The uploaded file is empty."))

        # We need to find the header row.
        # We will scan the first 10 rows to find a cell containing 'NAME'.
        header_row_idx = None
        for row_idx, row in enumerate(all_rows[:10]):
            if any(cell and isinstance(cell, str) and 'NAME' in cell.upper() for cell in row):
                header_row_idx = row_idx
                break

        if header_row_idx is None:
            raise UserError(_("Could not find a header row containing 'NAME'. Please ensure the standard template is used."))

        # Map column indexes based on header row
        headers = [str(cell).upper().strip() if cell else '' for cell in all_rows[header_row_idx]]
        
        try:
            name_idx = headers.index('NAME')
            student_no_idx = headers.index('STUDENT NUMBER')
            parent_no_idx = headers.index('PARENT NUMBER')
        except ValueError as e:
            raise UserError(_("Missing mandatory columns: NAME, STUDENT NUMBER, PARENT NUMBER"))

        # Detect semester columns. They typically contain 'sem'
        semester_cols = {}
        for idx, header in enumerate(headers):
            if 'SEM' in header:
                semester_cols[idx] = header

        student_obj = self.env['institute.accounting.student']
        semester_obj = self.env['institute.semester']

        # Cache semester masters to avoid creating duplicates
        sem_cache = {}
        for sem_name in semester_cols.values():
            sem_master = semester_obj.search([('name', '=ilike', sem_name)], limit=1)
            if not sem_master:
                sem_master = semester_obj.create({'name': sem_name})
            sem_cache[sem_name] = sem_master.id

        created_count = 0
        for row in all_rows[header_row_idx + 1:]:
            # Skip empty rows or "TOTAL" rows
            if len(row) <= name_idx or not row[name_idx] or 'TOTAL' in str(row[name_idx]).upper():
                continue

            name = str(row[name_idx]).strip()
            student_no = str(row[student_no_idx]).strip() if row[student_no_idx] is not None else ''
            parent_no = str(row[parent_no_idx]).strip() if row[parent_no_idx] is not None else ''

            fee_lines = []
            for col_idx, sem_name in semester_cols.items():
                fee_val = row[col_idx]
                
                # If None, empty, or not a number, treat as 0
                if fee_val in (None, '', '-'):
                    fee_amount = 0.0
                else:
                    try:
                        # Strip commas and parse
                        if isinstance(fee_val, str):
                            fee_val = fee_val.replace(',', '')
                        fee_amount = float(fee_val)
                    except ValueError:
                        fee_amount = 0.0

                if fee_amount >= 0:
                    fee_lines.append((0, 0, {
                        'semester_id': sem_cache[sem_name],
                        'total_fee': fee_amount,
                        'paid_amount': 0.0
                    }))

            # Find or Create Student
            student = student_obj.search([
                ('name', '=ilike', name), 
                ('branch_id', '=', self.branch_id.id),
                ('course_id', '=', self.course_id.id),
                ('batch_id', '=', self.batch_id.id)
            ], limit=1)

            if student:
                # To easily prevent duplicate fee lines, we can overwrite or just append.
                # In typical imports, we just append or skip if exists. 
                # We will simply overwrite old fees for simplicity:
                student.fee_line_ids.unlink()
                student.write({
                    'student_number': student_no,
                    'parent_number': parent_no,
                    'fee_line_ids': fee_lines
                })
            else:
                student_obj.create({
                    'name': name,
                    'branch_id': self.branch_id.id,
                    'course_id': self.course_id.id,
                    'batch_id': self.batch_id.id,
                    'student_number': student_no,
                    'parent_number': parent_no,
                    'fee_line_ids': fee_lines
                })
                created_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Successful'),
                'message': _('Successfully imported %s students and their dues.') % created_count,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }
