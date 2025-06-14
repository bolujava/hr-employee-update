from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import CacheMiss
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
import base64
import random
import string
import io
import csv
from xlsxwriter import Workbook

import logging

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
_logger.addHandler(console_handler)


class TrainingRequest(models.Model):
    _name = 'training.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Training Request'

    name = fields.Many2one("training.list", string="Course Title")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency")
    cost = fields.Float("Cost")
    # comment = fields.Text("Comment")
    start_date = fields.Date("Start Date", required=True)
    end_date = fields.Date("End Date", required=True)
    duration = fields.Integer(string='Duration', readonly=True, compute='_compute_duration')
    default_manager_user = fields.Many2one('res.users', related='manager_id.user_id', string="HOD")
    selected_employee_user = fields.Many2one('res.users', store=True)

    manager_id = fields.Many2one('hr.employee', "Line Manager", required=False, compute="_compute_manager_id",
                                 related='employee_id.department_id.manager_id',
                                 store=True,
                                 readonly=True,
                                 help="The manager of the employee's department.")
    # job_id = fields.Many2one('hr.job', related='employee_id.job_id', readonly=True)

    comment = fields.Text("Comments", required=False)
    planning_slot_ids = fields.One2many('planning.slot', 'training_id', string="Planning Slots")
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        default=lambda self: self._get_default_employee()
    )
    # job_id = fields.Many2one('hr.job', related='employee_id.job_id', readonly=True, string='Job Role')
    reference_id = fields.Char(
        string='Training Reference ID',
        compute='_compute_reference_id',
        store=True
    )
    report_id = fields.Many2one(
        'employee.training.report', string="Report"
    )
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'), ('submit', 'Submitted'), ('canceled', 'Canceled'),
                   ('pending', 'Pending Approval'), ('denied', 'Denied'),
                   ('line_manager', 'Line Manager Approved'), ('hr', 'HR'),
                   ], required=False, default='draft')

    assessment_score = fields.Float(
        string="Assessment Score",
        readonly=True,
        tracking=True
    )

    # selection=[('draft', 'Draft'), ('submit', 'Pending approval'),
    #             ('line_manager', 'Approved'), ('denied', 'Denied'),('canceled', 'Canceled')], required=False, default='draft')
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=True
    )
    hod_id = fields.Many2one(
        'hr.employee',
        string='Line Manager',
        related='department_id.manager_id',
        store=True,
        readonly=True
    )
    progress_percentage = fields.Float(
        string="Progress (%)",
        default=0.0,
        tracking=True
    )
    training_progress = fields.Selection(
        [
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        ],
        string="Training Progress",
        default='not_started',
        compute='_compute_training_progress',
        store=True,
        tracking=True
    )
    certificate_attachment_id = fields.Many2one('ir.attachment', string="Certificate Attachment", readonly=True,
                                                copy=False)  # New field
    active = fields.Boolean(string="Active", default=True)
    last_progress_update = fields.Datetime(string="Last Progress Update", readonly=True)
    approval_comment = fields.Text("Approval Comment", help="Manager's comment when approving the request.")
    denial_reason = fields.Text("Denial Reason", help="Reason for denying the request.")
    calendar_event_id = fields.Many2one('calendar.event', string="Calendar Event", readonly=True, copy=False)
    is_synced = fields.Boolean(string="Synced with Calendar", readonly=True, copy=False)

    def _recover_from_cache_miss(self):
        """Recover when cache misses occur"""
        self.env.cache.invalidate([(self._fields['training_progress'], self.ids)])
        # Recompute the field value
        self._compute_training_progress()

    @api.depends('name')
    def _compute_reference_id(self):
        for record in self:
            record.reference_id = record.name.reference_id if record.name else False

    @api.model
    def _get_default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id
            self.hod_id = self.department_id.manager_id
            self.manager_id = self.employee_id.parent_id

    def draft_method(self):
        self.state = "draft"

    # def submit_method(self):
    #     self.state = 'submit'
    def submit_method(self):
        self.check_eligibility()  # Perform eligibility check before submitting the request

        for record in self:
            if not record.hod_id:
                raise UserError("The employee's department does not have a line manager assigned.")

            if not record.hod_id.user_id:
                raise UserError(f"The manager {record.hod_id.name} does not have a linked user account.")
            company_partner_id = self.env.company.partner_id.id
            template_id = self.env.ref('training_management.email_template_training_request').id
            self.env['mail.template'].browse(template_id).send_mail(record.id, force_send=True)

            # Construct notification message
            message = (
                f"Dear {record.hod_id.name},\n\n"
                f"A new training request has been created by {record.employee_id.name} for the course '{record.name.name}'.\n"
                f"Comments: {record.comment or 'No comments provided.'}\n\n"
                f"Best regards,\nTraining Management System"
            )

            # Log the notification action
            _logger.info(f"Sending notification to manager {record.hod_id.name} (User ID: {record.hod_id.user_id.id})")

            # Send the message
            record.message_post(
                body=message,
                partner_ids=[record.hod_id.user_id.partner_id.id,
                             record.employee_id.user_id.partner_id.id],
                subject=f"New Training Request: {record.name.name}",
                email_from="operation@lotusbetaanalytics.com",  # Ensure email is from company
                author_id=company_partner_id
            )

            _logger.info("Notification successfully sent.")
            record.message_post(
                body="Your enrolment request has been submitted successfully.",
                partner_ids=[record.employee_id.user_id.partner_id.id],
                subject="Training Request Submission Confirmation"
            )
        self.state = 'submit'

    def cancel_training_request(self):
        for record in self:
            # Ensure the record is in a state that can be canceled
            if record.state not in ['draft', 'submit']:
                raise UserError("This request cannot be canceled in its current state.")

            record.unsync_from_calendar()
            company_partner_id = self.env.company.partner_id.id
            template_id = self.env.ref('training_management.email_template_training_request_cancel').id
            # Send email using the template
            self.env['mail.template'].browse(template_id).send_mail(record.id, force_send=True)
            # Update the state to 'canceled'
            record.state = 'canceled'

            # Prepare the message to be sent
            message = (
                f"Dear {record.employee_id.name},\n\n"
                f"Your training request for the course '{record.name.name}' has been canceled.\n\n"
                f"Best regards,\nTraining Management System"
            )

            # Notify the employee and HOD
            record.message_post(
                body=message,
                partner_ids=[
                    record.employee_id.user_id.partner_id.id,
                    record.hod_id.user_id.partner_id.id
                ],
                subject=f"Training Request Canceled: {record.name.name}",
                email_from="operation@lotusbetaanalytics.com",  # Ensure email is from company
                author_id=company_partner_id
            )

    def cancel_method(self):
        self.write({'state': 'draft'})

    def line_manager_approve_method(self):
        for record in self:
            if self.env.user != record.manager_id.user_id:
                raise UserError("Only the Line Manager can approve this request.")
            record.state = 'line_manager'
            record.sync_with_calendar()
            company_partner_id = self.env.company.partner_id.id
            template_id = self.env.ref('training_management.email_template_training_request_approved').id
            # Send email using the template
            self.env['mail.template'].browse(template_id).send_mail(record.id, force_send=True)
            # Notify the employee
            message = (
                f"Dear {record.employee_id.name},\n\n"
                f"Your training request for the course '{record.name.name}' has been approved.\n\n"
                f"Best regards,\nTraining Management System"
            )
            record.message_post(
                body=message,
                partner_ids=[record.employee_id.user_id.partner_id.id],
                subject=f"Training Request Approved: {record.name.name}",
                email_from="operation@lotusbetaanalytics.com",  # Ensure email is from company
                author_id=company_partner_id
            )

    def line_manager_deny_method(self):
        for record in self:
            if self.env.user != record.manager_id.user_id:
                raise UserError("Only the Line Manager can deny this request.")

            if not record.comment:
                raise UserError("Please provide a reason for denying the training request.")

            record.state = 'denied'
            company_partner_id = self.env.company.partner_id.id
            template_id = self.env.ref('training_management.email_template_training_request_denied').id
            # Send email using the template
            self.env['mail.template'].browse(template_id).send_mail(record.id, force_send=True)

            # Notify the employee
            message = (
                f"Dear {record.employee_id.name},\n\n"
                f"Your training request for the course '{record.name.name}' has been denied.\n\n"
                f"Reason for denial: {record.comment}\n\n"
                # f"Best regards,\nTraining Management System"
            )
            record.message_post(
                body=message,
                partner_ids=[record.employee_id.user_id.partner_id.id],
                subject=f"Training Request Denied: {record.name.name}",
                email_from="operation@lotusbetaanalytics.com",  # Ensure email is from company
                author_id=company_partner_id
            )

    def _current_login_employee_department(self):
        """Get the employee department record related to the current login user."""
        hr_employee = self.env['hr.employee.public'].search(
            [('user_id', '=', self._current_login_user())], limit=1)
        return hr_employee.department_id.id if hr_employee else False

    def _current_login_employee(self):
        hr_employee = self.env['hr.employee.public'].search(
            [('user_id', '=', self._current_login_user())], limit=1)
        return hr_employee.id if hr_employee else False

    @api.depends('manager_id')
    def _compute_is_line_manager(self):
        for record in self:
            record.is_line_manager = (
                    record.manager_id and
                    record.manager_id.user_id and
                    record.manager_id.user_id.id == self.env.uid
            )

    def _recover_from_cache_miss(self):
        """Recover when cache misses occur"""
        try:
            self.env.cache.invalidate([(self._fields['training_progress'], self.ids)])
            self.env.cache.invalidate([(self._fields['progress_percentage'], self.ids)])
            self._compute_training_progress()
            self.write({})  # Empty write to trigger cache update
            _logger.info(f"Cache recovered for record {self.id}")
        except Exception as error:
            _logger.error(f"Cache recovery failed for record {self.id}: {str(error)}")
            raise

    @api.depends('progress_percentage')
    def _compute_training_progress(self):
        for record in self:
            if not record.progress_percentage:
                record.training_progress = 'not_started'
            elif record.progress_percentage >= 100.0:
                if record.training_progress != 'completed':  # Only send if state is changing to completed
                    record.training_progress = 'completed'
                    record._send_training_completion_notification()
            elif 0 < record.progress_percentage < 100:
                record.training_progress = 'in_progress'
            else:
                record.training_progress = 'not_started'

    @api.onchange('progress_percentage')
    def _onchange_progress_percentage(self):
        for record in self:
            try:
                if not record.progress_percentage:
                    record.training_progress = 'not_started'
                    continue

                _logger.info(f"Updating progress for record {record.id}: {record.progress_percentage}%")

                if record.progress_percentage >= 100.0:
                    record.progress_percentage = 100.0
                    record.training_progress = 'completed'
                    _logger.info(f"Training completed for record {record.id}")
                elif 0 < record.progress_percentage < 100:
                    record.training_progress = 'in_progress'
                else:
                    record.training_progress = 'not_started'

                record.last_progress_update = fields.Datetime.now()

            except Exception as error:
                _logger.error(f"Error updating progress for record {record.id}: {str(error)}")
                continue

    def check_eligibility(self):
        for record in self:
            # Check if the employee's department is eligible
            if record.employee_id.department_id != record.name.department_id:
                raise UserError("You are not eligible to enrol in this training course based on your department.")

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            record.duration = (record.end_date - record.start_date).days if record.start_date and record.end_date else 0

    def send_progress_reminders(self):
        now = fields.Datetime.now()
        training_requests = self.search([
            ('training_progress', '=', 'in_progress'),
        ])
        _logger.info(f"Found {len(training_requests)} training requests in progress.")

        for training_request in training_requests:
            # Skip if the training has no start date, end date, or last progress update
            if not training_request.start_date or not training_request.end_date or not training_request.last_progress_update:
                continue

            # Calculate the time elapsed since the last progress update
            last_update = training_request.last_progress_update
            time_since_last_update = now - last_update

            # Calculate the training duration in days
            training_duration = (training_request.end_date - training_request.start_date).days

            # Determine the reminder threshold based on the training duration
            if training_duration <= 1:
                threshold = timedelta(minutes=2)  # 6 hours for one-day trainings
            else:
                threshold = timedelta(days=3)  # 3 days for longer trainings

            _logger.info(
                f"Training request {training_request.id}: Time since last update = {time_since_last_update}, Threshold = {threshold}.")

            # Send a reminder if no progress is made within the threshold
            if time_since_last_update >= threshold:
                training_request.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=training_request.employee_id.user_id.id,
                    note=f"Reminder: No progress has been made on your training '{training_request.name.name}' in the last {threshold}. Please update your progress.",
                    summary="Training Progress Reminder"
                )
                training_request.message_post(
                    body=f"Reminder: No progress has been made on your training '{training_request.name.name}' in the last {threshold}. Please update your progress.",
                    subject="Training Progress Reminder",
                    partner_ids=[training_request.employee_id.user_id.partner_id.id],
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment"
                )
                _logger.info(f"Email notification sent to {training_request.employee_id.user_id.partner_id.email}")
            else:
                _logger.info(f"No reminder needed for training request {training_request.id}.")

    @api.constrains('name', 'capacity', 'cost', 'currency_id', 'start_date', 'end_date')
    def _check_required_fields(self):
        for record in self:
            if not record.name:
                raise UserError("The 'Training Name' field is required.")
            if not record.start_date:
                raise UserError("The 'Start Date' field is required.")
            if not record.end_date:
                raise UserError("The 'End Date' field is required.")

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                duration = (record.end_date - record.start_date).days
                if duration < 0:
                    raise UserError("start date cannot be later than end date.")
                record.duration = duration
            else:
                record.duration = 0

    @api.depends('employee_id')
    def _compute_is_current_user_employee(self):
        for record in self:
            record.is_current_user_employee = record.employee_id.user_id.id == self.env.uid

    @api.depends("hod_id")
    def _compute_is_current_user_hod(self):
        for record in self:
            record.reference_id = record.name.reference_id if record.name else False

    @api.model
    def _get_default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id
            self.hod_id = self.department_id.manager_id

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            record.duration = (record.end_date - record.start_date).days if record.start_date and record.end_date else 0

    def _generate_certificate_pdf(self):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)

        # Set title
        pdf.setFont("Helvetica-Bold", 24)
        pdf.drawCentredString(300, 750, "Certificate of Completion")

        # Add employee name
        pdf.setFont("Helvetica", 18)
        pdf.drawCentredString(300, 700, f"Awarded to: {self.employee_id.name}")
        pdf.setFont("Helvetica", 16)
        pdf.drawCentredString(300, 650, f"For successfully completing the {self.name.name} training program.")

        # Completion date
        pdf.setFont("Helvetica", 14)
        pdf.drawCentredString(300, 600, f"Date of Completion: {self.write_date.strftime('%d %B %Y')}")

        # Add signature
        pdf.setFont("Helvetica-Oblique", 14)
        pdf.drawCentredString(300, 570, "LOTUS BETA ANALYTICS")
        pdf.drawCentredString(300, 530, "Training Manager")

        # Save and return PDF
        pdf.showPage()
        pdf.save()

        buffer.seek(0)
        return buffer.read()

    def _generate_certificate_attachment(self):
        pdf_content = self._generate_certificate_pdf()  # This function should return PDF binary content
        if not pdf_content:
            raise UserError("Failed to generate PDF content for the certificate.")
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        filename = f"Certificate_{self.employee_id.name or 'Unknown'}_{self.name.name or 'Training'}.pdf"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': pdf_base64,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })

        self.certificate_attachment_id = attachment.id  # Store attachment for later use

    def _send_training_completion_notification(self):
        for record in self:
            if not record.employee_id:
                raise UserError("This employee has not applied for this training!")

            # Generate certificate if missing
            if not record.certificate_attachment_id:
                record._generate_certificate_attachment()
            elif not record.certificate_attachment_id.name:
                # Additional safety check
                raise UserError("Certificate attachment exists but is missing a filename!")

            # Validate email
            email_to = record.employee_id.work_email
            _logger.info(f"Attempting to send email to: {email_to}")
            if not email_to:
                _logger.warning(f"No valid email for employee {record.employee_id.name} (ID: {record.employee_id.id})")
                raise UserError(f"No valid email found for employee {record.employee_id.name}")

            company_partner_id = self.env.company.partner_id.id
            # Internal notification (Chatter)
            message = (
                f"Dear {record.employee_id.name},\n\n"
                f"You have just successfully completed the '{record.name.name}' with {record.reference_id}. \n"
                f"Attached to this email is your certificate of completion for the training. \n\n"
                f"Best regards,\nTraining Management System"
            )
            _logger.info(f"Sending notification to manager {record.hod_id.name} (User ID: {record.hod_id.user_id.id})")
            # record.message_subscribe(partner_ids=[record.employee_id.user_id.partner_id.id])
            record.message_post(
                body=message,
                # partner_ids=[record.employee_id.user_id.partner_id.id],
                subject=f"New Training Course Completed: {record.name.name}",
                email_from="operation@lotusbetaanalytics.com",
                email_to=email_to,
                author_id=company_partner_id,
                attachment_ids=[record.certificate_attachment_id.id],  # Correct format
                message_type='comment',
                subtype_id=self.env.ref('mail.mt_comment').id,
                notification_ids=False  # Disable auto-notifications
            )
            _logger.info(f"Email sent ONLY to employee: {record.employee_id.name}")

            if record.hod_id and record.hod_id.user_id:
                manager_email = record.hod_id.work_email or record.hod_id.user_id.email
                if not manager_email:
                    _logger.warning(f"No email found for manager {record.hod_id.name}")
                    continue
                manager_message = (
                    f"Dear {record.hod_id.name},\n\n"
                    f"Your team member {record.employee_id.name} has successfully completed "
                    f"the '{record.name.name}' training with {record.reference_id}.\n\n"
                    f"Best regards,\nTraining Management System"
                )

                mail_values = {
                    'subject': f"Team Member Training Completed: {record.name.name}",
                    'body_html': manager_message,
                    'email_from': "operation@lotusbetaanalytics.com",
                    'email_to': manager_email,
                    'author_id': company_partner_id,
                    'model': record._name,
                    'res_id': record.id,
                }
                self.env['mail.mail'].sudo().create(mail_values).send()
                _logger.info(f"Email sent to manager: {record.hod_id.name}")

    def test_send_completion_notification(self):
        """Test method for sending completion notification"""
        self.ensure_one()
        try:
            self._check_can_send_notification()
            if self.training_progress != 'completed':
                self.progress_percentage = 100
            result = self._send_training_completion_notification()
            if result:
                raise UserError(f"Test notification sent successfully to {self.employee_id.name}!")
            else:
                raise UserError("Failed to send test notification")
        except Exception as e:
            raise UserError(str(e))


    def sync_with_calendar(self):
        for record in self:
            # Check if an event already exists
            event_vals = {
                'name': f'Training: {record.name.name}',
                'description': f"Training Course: {record.name.name}\nDuration: {record.duration} days\nComments: {record.comment}",
                'start': record.start_date,
                'stop': record.end_date,
                'allday': True,
                'partner_ids': [(6, 0, [record.employee_id.user_id.partner_id.id])],
            }
            if record.calendar_event_id:
                event = self.env['calendar.event'].browse(int(record.calendar_event_id))
                if event.exists():
                    event.write(event_vals)
                else:
                    new_event = self.env['calendar.event'].create(event_vals)
                    record.calendar_event_id = new_event.id
            else:
                new_event = self.env['calendar.event'].create(event_vals)
                record.calendar_event_id = new_event.id

            record.is_synced = True
            record.message_post(
                body=f"The '{record.name.name}' schedule has been synced with your personal calendar.",
                partner_id=[record.employee_id.user_id.partner_id.id],
                subject="Calendar Synced successfully !"
            )


    def unsync_from_calendar(self):
        for record in self:
            if record.calendar_event_id:
                event = self.env['calendar.event'].browse(record.calendar_event_id)
                event.unlink()
                record.calendar_event_id = False
                record.is_synced = False
                record.message_post(
                    body=f"Training schedule for  '{record.name.name}' has been removed from your personal calendar.",
                    partner_ids=[record.employee_id.user_id.partner_id.id],
                    subject="Calendar Unsynced Successfully !"
                )


    def create_calendar_event(self):
        for record in self:
            if not record.employee_id.user_id or not record.employee_id.user_id.partner_id:
                raise UserError("Employee must have a linked user and partner to create a calendar event.")

            event = self.env['calendar.event'].create({
                'name': f"Training: {record.name.name}",
                'start': record.start_date,
                'stop': record.end_date,
                'description': f"Training Course: {record.name.name}\nDuration: {record.duration} days\nComments: {record.comment}",
                'partner_ids': [(4, record.employee_id.user_id.partner_id.id)],
                'user_id': record.employee_id.user_id.id,
                'res_model': 'training.request',
                'res_id': record.id,
            })
            record.calendar_event_id = event.id
            record.is_synced = True
            _logger.info(f"Calendar event created for training request {record.id}: {event.name}")
        return event


class Employee(models.Model):
    _inherit = 'hr.employee'
    work_email = fields.Char(string="Work Email")
