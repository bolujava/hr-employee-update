# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
import pytz
from odoo.exceptions import UserError
import random
import string
from datetime import timedelta
from datetime import datetime, timedelta
import base64




_logger = logging.getLogger(__name__)


class TrainingModule(models.Model):
    _name = 'training.list'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'TrainingModule'

    name = fields.Char("Training Name", required=True)
    user_id = fields.Many2one('res.users', string="Responsible User")
    capacity = fields.Integer("Capacity", required=True)
    cost = fields.Monetary(string='Amount', currency_field="currency_id", required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    comment = fields.Text("Comment")
    start_date = fields.Date("Start Date", required=True)
    end_date = fields.Date("End Date", required=True)
    duration = fields.Integer(
        string="Duration (Days)",
        compute="_compute_duration",
        store=True
    )
    training_quarter = fields.Selection(
        [('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4')],
        string="Quarter", compute='_compute_quarter_year', store=True
    )
    training_year = fields.Integer(string="Year", compute='_compute_quarter_year', store=True)

    reference_id = fields.Char(string="Reference ID", readonly=True, copy=False)
    description = fields.Text("Description", help="Details about the training course.")

    # last_progress_date = fields.Datetime(string="Last Progress Date")
    reminder_sent = fields.Boolean(string="Reminder Sent", default=False)
    department_id = fields.Many2one(
        'hr.department',
        string="Primary Department",
        help="Primary department responsible for this training"
    )
    employee_ids = fields.Many2many(
        'hr.employee', 
        string="Assigned Employees", 
        domain="[('department_id', '=', department_id)]",
        help="Employees assigned to this training by their department manager."
    )
    allowed_roles = fields.Many2many('hr.job', string='Allowed Roles')  # Roles eligible for the course

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        help="Employee responsible for the training",
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string="Department Manager",
        compute="_compute_manager_id",
        store=True
    )
    schedule = fields.Char(string="Schedule", compute="_compute_schedule", store=True, help="This field dynamically displays the training's schedule based on the quarter and year."
    )
      
    eligibility_requirements = fields.Text(
        string="Eligibility Requirements",
        help="Prerequisites or requirements for participants."
    )
    
    def _generate_ics_content(self, training):
        """Generate ICS file content for the training schedule."""
        start_datetime = datetime.combine(training.start_date, datetime.min.time()) + timedelta(hours=9)
        end_datetime = datetime.combine(training.end_date, datetime.min.time()) + timedelta(hours=17)
         # Convert to string for ICS format (YYYYMMDDTHHMMSS)
        start_datetime_str = start_datetime.strftime('%Y%m%dT%H%M%S')
        end_datetime_str = end_datetime.strftime('%Y%m%dT%H%M%S')
    
        # start_datetime = fields.Datetime.to_string(training.start_date + " 09:00:00")
        # end_datetime = fields.Datetime.to_string(training.end_date + " 17:00:00")
        
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Odoo//NONSGML v1.0//EN
BEGIN:VEVENT
SUMMARY:Training - {training.name}
DTSTART;TZID=America/New_York:{start_datetime_str}
DTEND;TZID=America/New_York:{end_datetime_str}
DESCRIPTION:{training.description or 'No description available'}
LOCATION:{training.department_id.name}
STATUS:CONFIRMED
BEGIN:VALARM
TRIGGER:-PT15M
DESCRIPTION:Reminder: Training - {training.name}
ACTION:DISPLAY
END:VALARM
END:VEVENT
END:VCALENDAR"""
        return ics_content
    
    
    
    def export_to_ics(self):
        """Export training details to an ICS file."""
        # Generate ICS content for the current training
        ics_content = self._generate_ics_content(self)
        
        # Encode to base64 to send as a download
        ics_file = base64.b64encode(ics_content.encode('utf-8')).decode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.name}_Training_Schedule.ics',
            'type': 'binary',
            'datas': ics_file,
            'mimetype': 'text/calendar',
            'res_model': 'training.list',
            'res_id': self.id
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
        
    @api.depends('training_quarter', 'training_year')
    def _compute_schedule(self):
        for record in self:
            if record.training_quarter and record.training_year:
                record.schedule = f"{record.training_quarter} {record.training_year}"
            else:
                record.schedule = "Not Scheduled"
    
    @api.depends('start_date')
    def _compute_quarter_year(self):
        for record in self:
            if record.start_date:
                # Extract the year and month from the start date
                start_date = fields.Date.from_string(record.start_date)
                record.training_year = start_date.year
                
                # Determine the quarter based on the month
                month = start_date.month
                if month in [1, 2, 3]:
                    record.training_quarter = 'Q1'
                elif month in [4, 5, 6]:
                    record.training_quarter = 'Q2'
                elif month in [7, 8, 9]:
                    record.training_quarter = 'Q3'
                else:
                    record.training_quarter = 'Q4'
        
    
    @api.model
    def create(self, vals):
        # Generate a unique reference ID that starts with 'T'
        if 'reference_id' not in vals or not vals['reference_id']:
            reference_id = self._generate_reference_id()
            vals['reference_id'] = reference_id
            # current_user = self.env.user
            # employee = self.env['hr.employee'].search([('user_id', '=', current_user.id)], limit=1)
            # if not employee:
            #     raise UserError("No employee record found for the current user.")
            # if employee.department_id.manager_id != employee:
            #     raise UserError("You are not authorized to create training for this department.")
            # if 'department_id' in vals:
            #      department_id = vals['department_id']
            #      if department_id != employee.department_id.id:
            #          raise UserError("You can only create training for your own department.")
                 



            
            record = super(TrainingModule, self).create(vals)
            
            
            ics_content = self._generate_ics_content(record)
            _logger = logging.getLogger(__name__)
            _logger.info(f"Generated ICS Content:\n{ics_content}")
            
            self._send_notification_to_employees(record)
            return record
           
            # Fix: Reference the correct model for super() call
        return super(TrainingModule, self).create(vals)
     

    @api.constrains('name', 'capacity', 'cost', 'currency_id', 'start_date', 'end_date')
    def _check_required_fields(self):
        for record in self:
            if not record.name:
                raise UserError("The 'Training Name' field is required.")
            if not record.capacity:
                raise UserError("The 'Capacity' field is required.")
            if not record.cost:
                raise UserError("The 'Amount' field is required.")
            if not record.currency_id:
                raise UserError("The 'Currency' field is required.")
            if not record.start_date:
                raise UserError("The 'Start Date' field is required.")
            if not record.end_date:
                raise UserError("The 'End Date' field is required.")

    def _generate_reference_id(self):
        """Generates a unique reference ID starting with TM"""
        unique_suffix = ''.join(random.choices(string.digits, k=6))  # 6-digit random number
        return f"TM{unique_suffix}"
    
    def _send_notification_to_employees(self, record):
        """Sends notification to employees in the department of the training."""
    # Fetch employees in the department
        employees = self.env['hr.employee'].search([('department_id', '=', record.department_id.id)])
        for employee in employees:
            message = (
                f"Dear {employee.name},\n\n"
                f"A new training course '{record.name}' has been created in your department ({record.department_id.name}).\n"
                f"Training Start Date: {record.start_date}\n"
                f"Training End Date: {record.end_date}\n\n"
                
                f"Best regards,\nTraining Management System"
                )
            record.message_post(
            body=message,
            partner_ids=[employee.user_id.partner_id.id],
            subject=f"New Training Course: {record.name}"
        )
            assigned_employees = self.env['hr.employee'].search([('id', 'in', record.employee_ids.ids)])
            for employee in assigned_employees:
                message = (
                     f"Dear {employee.name},\n\n"
            f"You have been assigned to the training course '{record.name}'.\n"
            f"Training Start Date: {record.start_date}\n"
            f"Training End Date: {record.end_date}\n\n"
            f"Please make sure to attend as per the schedule.\n\n"
            f"Best regards,\nTraining Management System"
        )
                record.message_post(
            body=message,
            partner_ids=[employee.user_id.partner_id.id],
            subject=f"Training Assignment: {record.name}"
        )   
            
        

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


    @api.constrains('department_id', 'manager_id')
    def _check_department_manager(self):
        for record in self:
            if not record.department_id:
                raise UserError("A department must be selected for the training.")
            if not record.manager_id:
                raise UserError("The selected department does not have a manager assigned.")


    @api.depends('department_id')
    def _compute_manager_id(self):
        for record in self:
            manager = False
            if record.department_id:
                manager = record.department_id.manager_id
                if not manager and record.department_id.parent_id:
                    manager = record.department_id.parent_id.manager_id
            _logger.info(f"Computed Manager: {manager}")
            record.manager_id = manager

    def assign_employees_to_training(self, employee_ids):
        """Allow Department Managers to assign employees to training."""
        for record in self:
            if record.manager_id.user_id != self.env.user:
                raise UserError("You are not authorized to assign employees to this training.")
            record.employee_ids = [(6, 0, employee_ids)]
    
   

            
class HrDepartment(models.Model):
    _inherit = 'hr.department'


    manager_id = fields.Many2one('hr.employee', string="Manager")
    report_id = fields.Many2one('employee.training.report', string="Training Report")







