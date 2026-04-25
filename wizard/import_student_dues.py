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
            if any(cell and isinstance(cell, str) and ('NAME' in cell.upper() or 'NAME OF THE STUDENT' in cell.upper()) for cell in row):
                header_row_idx = row_idx
                break

        if header_row_idx is None:
            raise UserError(_("Could not find a header row containing 'NAME'. Please ensure the standard template is used."))

        # Map column indexes based on header row
        headers = [str(cell).upper().strip() if cell else '' for cell in all_rows[header_row_idx]]
        
        name_idx = -1
        student_no_idx = -1
        parent_no_idx = -1
        
        for idx, h in enumerate(headers):
            if 'NAME' in h:
                name_idx = idx
            elif 'STUDENT' in h and ('CONTACT' in h or 'NUMBER' in h or 'NO' in h):
                student_no_idx = idx
            elif 'PARENT' in h and ('CONTACT' in h or 'NUMBER' in h or 'NO' in h):
                parent_no_idx = idx

        if name_idx == -1:
            raise UserError(_("Could not find a column containing 'NAME'."))

        is_two_row_header = False
        next_row = []
        if len(all_rows) > header_row_idx + 1:
            next_row = [str(cell).upper().strip() if cell else '' for cell in all_rows[header_row_idx + 1]]
            if any('TO BE PAID' in cell for cell in next_row):
                is_two_row_header = True

        semester_cols = {} # dict of sem_name -> {'total_idx': idx, 'paid_idx': idx}
        if is_two_row_header:
            current_fee_head = None
            for idx in range(len(headers)):
                h = headers[idx]
                if h:
                    is_known = any(kw in h for kw in ['SL.NO', 'SL NO', 'NAME', 'MERIT', 'CONTACT', 'PACKAGE', 'TOTAL'])
                    if not is_known:
                        current_fee_head = h
                
                if current_fee_head:
                    sub_h = next_row[idx] if idx < len(next_row) else ''
                    if 'TO BE PAID' in sub_h:
                        if current_fee_head not in semester_cols:
                            semester_cols[current_fee_head] = {'total_idx': None, 'paid_idx': None}
                        semester_cols[current_fee_head]['total_idx'] = idx
                    elif sub_h == 'PAID':
                        if current_fee_head not in semester_cols:
                            semester_cols[current_fee_head] = {'total_idx': None, 'paid_idx': None}
                        semester_cols[current_fee_head]['paid_idx'] = idx
            data_start_idx = header_row_idx + 2
        else:
            for idx, header in enumerate(headers):
                if 'SEM' in header:
                    semester_cols[header] = {'total_idx': idx, 'paid_idx': None}
            data_start_idx = header_row_idx + 1

        student_obj = self.env['institute.accounting.student']
        semester_obj = self.env['institute.semester']

        # Cache semester masters to avoid creating duplicates
        sem_cache = {}
        for sem_name in semester_cols.keys():
            sem_master = semester_obj.search([('name', '=ilike', sem_name)], limit=1)
            if not sem_master:
                sem_master = semester_obj.create({'name': sem_name})
            sem_cache[sem_name] = sem_master.id

        created_count = 0
        for row in all_rows[data_start_idx:]:
            # Skip empty rows or "TOTAL" rows
            if len(row) <= name_idx or not row[name_idx] or 'TOTAL' in str(row[name_idx]).upper():
                continue

            name = str(row[name_idx]).strip()
            student_no = str(row[student_no_idx]).strip() if student_no_idx != -1 and row[student_no_idx] is not None else ''
            parent_no = str(row[parent_no_idx]).strip() if parent_no_idx != -1 and row[parent_no_idx] is not None else ''

            fee_lines = []
            for sem_name, cols in semester_cols.items():
                total_idx = cols['total_idx']
                paid_idx = cols['paid_idx']
                
                total_val = row[total_idx] if total_idx is not None and total_idx < len(row) else 0.0
                paid_val = row[paid_idx] if paid_idx is not None and paid_idx < len(row) else 0.0
                
                def parse_amount(val):
                    if val in (None, '', '-'): return 0.0
                    try:
                        if isinstance(val, str): val = val.replace(',', '')
                        return float(val)
                    except ValueError: return 0.0

                fee_amount = parse_amount(total_val)
                paid_amount = parse_amount(paid_val)

                if fee_amount >= 0 or paid_amount > 0:
                    fee_lines.append((0, 0, {
                        'semester_id': sem_cache[sem_name],
                        'total_fee': fee_amount,
                        'paid_amount': paid_amount
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
