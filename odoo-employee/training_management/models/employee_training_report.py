import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
import csv
import xlsxwriter
from io import BytesIO

_logger = logging.getLogger(__name__)


class EmployeeTrainingReport(models.Model):
    _name = 'employee.training.report'
    _description = 'Employee Training Report'

    name = fields.Char(string="Report Name", required=True)
    scope = fields.Selection(
        [
            ('by_department', 'All Trainings of Employees Within a Department'),
            ('organization_wide', 'All Trainings of All Departments'),
            ('by_employee', 'All Trainings of a Specific Employee Within a Department')
        ],
        string="Scope",
        required=True,
        default='by_department'
    )
    department_id = fields.Many2one('hr.department', string="Department")
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        domain="[('department_id', '=', department_id)]",
        help="If you want to generate a report for one employee."
    )
    report_file = fields.Binary(string="DOWNLOAD", readonly=True)
    report_file_name = fields.Char(string="Report File Name")
    report_format = fields.Selection([('csv', 'CSV'), ('xlsx', 'Excel (xslsx)'), ('pdf', 'PDF')], string="Report Format", default='csv', required=True, help="Select the format in which the report should be generated."
)


    @api.model
    def create_report(self, department_id, start_date, end_date, employee_id=None, file_format='csv'):
        print("Create report method called with args:")
        print(department_id, start_date, end_date, employee_id)
        _logger.info("Department ID: %s, Start Date: %s, End Date: %s", department_id.id, start_date, end_date)

        """ Create the training report for all employees in a department or for a single employee """
        if not start_date or not end_date:
            raise UserError("Start Date and End Date are required to generate the report.")

        # Fetch relevant data
        trainings = self._get_trainings(department_id, start_date, end_date, employee_id)

        if not trainings:
            raise UserError("No training records found for the specified criteria.")

        # Generate the report in CSV and XLSX formats
        report_file, report_file_name = self.generate_report(trainings, file_format)

        # Create report record in the system
        report_name = "Training Report"

        # Include the "name" field if provided
        if self.name:
            report_name = f"{self.name} - {report_name}"

        # Add department name if available
        if department_id and department_id.name:
            report_name = f"{report_name} ({department_id.name})"

        # Determine the file extension based on the file_format
        file_extension = ''
        if file_format == 'csv':
            file_extension = '.csv'
        elif file_format == 'xlsx':
            file_extension = '.xlsx'
        elif file_format == 'pdf':
            file_extension = '.pdf'

        # Generate the full file name
        report_file_name = f"{report_name}{file_extension}"

        # Create the report record
        report = self.create({
            'name': report_name,
            'department_id': department_id.id,
            'start_date': start_date,
            'end_date': end_date,
            'employee_id': employee_id.id if employee_id else False,
            'report_file': report_file,
            'report_file_name': report_file_name
        })
        return report

    @api.onchange('scope')
    def _onchange_scope(self):
        """ Adjust available fields based on the selected scope """
        if self.scope == 'organization_wide':
            self.department_id = False
            self.employee_id = False
        elif self.scope == 'by_department':
            self.employee_id = False
        elif self.scope == 'by_employee':
            if not self.department_id:
                self.employee_id = False

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """ Clear employee_id if department changes """
        self.employee_id = False

    @api.onchange('report_file')
    def _onchange_report_file(self):
        # Ensure name is not updated unnecessarily
        if self.name and '(False)' in self.name:
            self.name = self.name.replace('(False)', '').strip()

    def button_create_report(self):
        """ Trigger the report creation process and open the result. """
        self.ensure_one()
        file_format = self.report_format
        report = self.create_report(self.department_id, self.start_date, self.end_date, self.employee_id, file_format=file_format)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generated Report',
            'res_model': 'employee.training.report',
            'res_id': report.id,  # Open the specific report
            'view_mode': 'form',
            'target': 'new',
        }

    def button_generate_and_download_report(self):
        """Generate the report and trigger the download immediately."""
        self.ensure_one()

        # Generate the report
        file_format = self.report_format
        report = self.create_report(self.department_id, self.start_date, self.end_date, self.employee_id,
                                    file_format=file_format)

        # Prepare the download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/employee.training.report/{report.id}/report_file/{report.report_file_name}?download=true',
            'target': 'self',
        }


    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}

    def _get_trainings(self, department_id, start_date, end_date, employee_id=None, scope='by_department'):
        """ Fetch training data based on the selected scope """
        domain = [('start_date', '>=', start_date), ('end_date', '<=', end_date)]

        if scope == 'by_department' and department_id:
            domain.append(('department_id', '=', department_id.id))
        elif scope == 'by_employee' and employee_id:
            domain.append(('employee_id', '=', employee_id.id))
        elif scope == 'organization_wide':
            if not department_id and not employee_id:
                _logger.warning("Fetching organization-wide training without specific filters.")

        domain.append(('state', '=', 'line_manager'))

        trainings = self.env['training.request'].search(domain)
        _logger.info("Trainings fetched: %s", trainings)
        return trainings

    def generate_report(self, trainings, file_format='csv'):
        if file_format == 'csv':
            report_file = self.generate_csv_report(trainings)
            report_file_name = "employee_training_report.csv"
        elif file_format == 'xlsx':
            report_file = self.generate_xlsx_report(trainings)
            report_file_name = "employee_training_report.xlsx"
        elif file_format == 'pdf':
            report_file = self.generate_pdf_report(trainings)
            report_file_name = "employee_training_report.pdf"
        else:
            raise UserError("Unsupported file format. Please choose CSV or XLSX or PDF.")
        return report_file, report_file_name

    def generate_csv_report(self, trainings):
        """ Generate CSV format report """
        csv_output = io.StringIO()
        fieldnames = ['Training Name', 'Employee', 'Department', 'Start Date', 'End Date', 'Duration', 'Progress (%)',
                      'Training Progress']
        writer = csv.DictWriter(csv_output, fieldnames=fieldnames)
        writer.writeheader()

        for training in trainings:
            # Instead of checking for attendees, use employee_id directly
            employee = training.employee_id  # The requestor and attendee are the same in this case
            department = employee.department_id  # Get the department of the employee
            _logger.info("Processing training for: %s", employee.name)

            writer.writerow({
                'Training Name': training.name.name,
                'Employee': employee.name,  # Using employee_id as the attendee
                'Department': department.name if department else "N/A",
                'Start Date': training.start_date,
                'End Date': training.end_date,
                'Duration': training.duration,
                # 'Cost': training.cost,
                'Progress (%)': training.progress_percentage,
                'Training Progress': training.training_progress
            })

        csv_output.seek(0)
        return base64.b64encode(csv_output.getvalue().encode('utf-8'))


    def generate_xlsx_report(self, trainings):
        """ Generate XLSX format report """
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Employee Training Report')

        headers = ['Training Name', 'Employee', 'Department', 'Start Date', 'End Date', 'Duration', 'Progress (%)',
                   'Training Progress']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header)

        row = 1
        for training in trainings:
            employee = training.employee_id  # Again, only use employee_id as the attendee
            department = employee.department_id
            _logger.info("Processing training for: %s", employee.name)

            worksheet.write(row, 0, training.name.name)
            worksheet.write(row, 1, employee.name)
            worksheet.write(row, 2, department.name if department else "N/A")
            worksheet.write(row, 3, str(training.start_date))
            worksheet.write(row, 4, str(training.end_date))
            worksheet.write(row, 5, training.duration)
            # worksheet.write(row, 6, training.cost)
            worksheet.write(row, 6, training.progress_percentage)
            worksheet.write(row, 7, training.training_progress)
            row += 1

        workbook.close()
        output.seek(0)
        return base64.b64encode(output.read())

    def generate_pdf_report(self, trainings):
        """Generate a well-formatted PDF report."""
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle("Employee Training Report")

        # Page settings
        margin = 30
        page_width, page_height = letter
        y_position = page_height - 50  # Start position for title

        # Title
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(margin, y_position, "Employee Training Report")
        y_position -= 30  # Move down for headers

        # Column headers
        pdf.setFont("Helvetica-Bold", 10)
        headers = ['Training Name', 'Employee', 'Department', 'Start Date', 'End Date', 'Duration', 'Progress',
                   'Status']
        column_widths = [100, 80, 100, 70, 70, 50, 60, 80]  # Column width adjustments
        x_positions = [margin + sum(column_widths[:i]) for i in range(len(column_widths))]

        # Draw headers
        for idx, header in enumerate(headers):
            pdf.drawString(x_positions[idx], y_position, header)

        y_position -= 20  # Move down for data

        # Populate data
        pdf.setFont("Helvetica", 9)
        row_height = 14  # Space between rows

        for training in trainings:
            employee = training.employee_id
            department = employee.department_id
            data = [
                training.name.name,
                employee.name,
                department.name if department else "N/A",
                str(training.start_date),
                str(training.end_date),
                str(training.duration),
                f"{training.progress_percentage}%",
                training.training_progress or "N/A",  # Ensure status is included
            ]

            # Determine the max number of lines needed for wrapping
            max_lines = 1  # Track max lines per row to ensure consistent spacing
            wrapped_data = []

            for idx, value in enumerate(data):
                wrapped_text = simpleSplit(value, "Helvetica", 9, column_widths[idx])  # Auto-wrap text
                wrapped_data.append(wrapped_text)
                max_lines = max(max_lines, len(wrapped_text))  # Track the tallest row

            # Ensure space for all lines in the row
            for line_idx in range(max_lines):
                for col_idx, lines in enumerate(wrapped_data):
                    if line_idx < len(lines):  # If this line exists
                        pdf.drawString(x_positions[col_idx], y_position, lines[line_idx])

                y_position -= row_height  # Move down for next line

            # Check for page break
            if y_position < 50:
                pdf.showPage()
                pdf.setFont("Helvetica", 9)
                y_position = page_height - 50  # Reset y_position

                # Re-draw headers on new page
                pdf.setFont("Helvetica-Bold", 10)
                pdf.line(margin, y_position + 5, page_width - margin, y_position + 5)

                for idx, header in enumerate(headers):
                    pdf.drawString(x_positions[idx], y_position, header)
                # y_position -= 5
                pdf.line(margin, y_position - 5, page_width - margin, y_position - 5)
                y_position -= 20
                pdf.setFont("Helvetica", 9)

        pdf.save()
        buffer.seek(0)
        return base64.b64encode(buffer.read())














































































    # def generate_xlsx_report(self, trainings):
    #     """ Generate XLSX format report """
    #     output = BytesIO()
    #     workbook = xlsxwriter.Workbook(output)
    #     worksheet = workbook.add_worksheet('Employee Training Report')
    #
    #     headers = ['Training Name', 'Employee', 'Start Date', 'End Date', 'Duration', 'Cost', 'Progress (%)',
    #                'Training Progress']
    #     for col_num, header in enumerate(headers):
    #         worksheet.write(0, col_num, header)
    #
    #     row = 1
    #     for training in trainings:
    #         if not trainings.attendee_ids:
    #             _logger.warning("Training %s has no attendee", training.name)
    #         else:
    #             for attendee in training.attendee_ids:  # Assuming `attendee_ids` exists on the training module
    #                 worksheet.write(row, 0, training.name)
    #                 worksheet.write(row, 1, attendee.name.name)
    #                 worksheet.write(row, 2, str(training.start_date))
    #                 worksheet.write(row, 3, str(training.end_date))
    #                 worksheet.write(row, 4, training.duration)
    #                 worksheet.write(row, 5, training.cost)
    #                 worksheet.write(row, 6, attendee.progress_percentage)
    #                 worksheet.write(row, 7, attendee.training_progress)
    #                 row += 1
    #
    #     workbook.close()
    #     output.seek(0)
    #     return base64.b64encode(output.read())

    # def generate_csv_report(self, trainings):
    #     """ Generate CSV format report """
    #     csv_output = io.StringIO()
    #     fieldnames = ['Training Name', 'Employee', 'Start Date', 'End Date', 'Duration', 'Cost', 'Progress (%)',
    #                   'Training Progress']
    #     writer = csv.DictWriter(csv_output, fieldnames=fieldnames)
    #     writer.writeheader()
    #
    #     for training in trainings:
    #         # Check if there are attendees
    #         if not training.attendee_ids:
    #             # Log a message and add a note in the report
    #             _logger.warning("Training %s has no attendees", training.name)
    #             writer.writerow({
    #                 'Training Name': training.name.name,
    #                 'Employee': "No Attendees",
    #                 'Start Date': training.start_date,
    #                 'End Date': training.end_date,
    #                 'Duration': training.duration,
    #                 'Cost': training.cost,
    #                 'Progress (%)': "N/A",
    #                 'Training Progress': "N/A"
    #             })
    #         else:
    #             # Process each attendee
    #             for attendee in training.attendee_ids:
    #                 _logger.info("Processing attendee: %s", attendee.name.name)
    #                 writer.writerow({
    #                     'Training Name': training.name,
    #                     'Employee': attendee.name.name,  # Assuming the field is a Many2one relation to `hr.employee`
    #                     'Start Date': training.start_date,
    #                     'End Date': training.end_date,
    #                     'Duration': training.duration,
    #                     'Cost': training.cost,
    #                     'Progress (%)': attendee.progress_percentage,
    #                     'Training Progress': attendee.training_progress
    #                 })
    #
    #     csv_output.seek(0)
    #     return base64.b64encode(csv_output.getvalue().encode('utf-8'))

    # def generate_csv_report(self, trainings):
    #     """ Generate CSV format report """
    #     csv_output = io.StringIO()
    #     fieldnames = ['Training Name', 'Employee', 'Start Date', 'End Date', 'Duration', 'Cost', 'Progress (%)',
    #                   'Training Progress']
    #     writer = csv.DictWriter(csv_output, fieldnames=fieldnames)
    #     writer.writeheader()
    #
    #     for training in trainings:
    #         if not training.attendee_ids:
    #             _logger.warning("Training %s has no attendees", training.name)
    #         else:
    #             # _logger.info("Processing training: %s", training.name)
    #             for attendee in training.attendee_ids:
    #                 # Assuming `attendee_ids` exists on the training module
    #                 writer.writerow({
    #                     'Training Name': training.name,
    #                     'Employee': attendee.name.name,  # Assuming the field is a Many2one relation to `hr.employee`
    #                     'Start Date': training.start_date,
    #                     'End Date': training.end_date,
    #                     'Duration': training.duration,
    #                     'Progress (%)': attendee.progress_percentage,
    #                     'Training Progress': attendee.training_progress
    #                 })
    #
    #
    #     csv_output.seek(0)
    #     return base64.b64encode(csv_output.getvalue().encode('utf-8'))



