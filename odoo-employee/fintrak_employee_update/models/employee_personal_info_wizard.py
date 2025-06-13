# models/employee_personal_info_wizard.py
from odoo import models, fields, api

class EmployeePersonalInfoWizard(models.TransientModel):
    _name = 'employee.personal.info.wizard'
    _description = 'Fill Personal Info Wizard'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, ondelete="cascade")
    identification_number = fields.Char()
    passport_number = fields.Char()
    birth_place = fields.Char()
    surname = fields.Char("Surname")
    first_name = fields.Char("First Name")
    middle_name = fields.Char("Middle Name")
    gender = fields.Selection([('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),], string='Gender')
    date_of_birth = fields.Date(string="Date of Birth")
    state_of_origin = fields.Char(string="State of Origin")
    lga = fields.Char(string="LGA")
    town = fields.Char(string="Town")
    contact_phone_number = fields.Char(string="Contact Phone Number")
    alternate_phone_number = fields.Char(string="Alternate Phone Number")
    means_of_identification = fields.Selection([
        ('nin', 'NIN'),
        ('passport', 'Passport'),
        ('driver_license', 'Driver\'s License'),
        ('voter_card', 'Voter\'s Card'),
        ('other', 'Other')
    ], string="Means of Identification")
    means_of_identification_number = fields.Char(string="Identification Number (e.g., NIN)")
    state_of_issuance = fields.Char(string="State of Issuance")
    address_of_employee = fields.Text(string="Address of Employee")
    job_title = fields.Char(string="Job Title")
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed')
    ], string="Marital Status")
    number_of_primary_dependants = fields.Integer(string="Number of Primary Dependants")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        employee_id = self.env.context.get('default_employee_id')
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            res.update({
                'employee_id': employee.id,
                'identification_number': employee.identification_number,
                'passport_number': employee.passport_number,
                'birth_place': employee.birth_place,
                'surname': employee.surname,
                'first_name': employee.first_name,
                'middle_name': employee.middle_name,
                'gender': employee.gender,
                'date_of_birth': employee.date_of_birth,
                'state_of_origin': employee.state_of_origin,
                'lga': employee.lga,
                'town': employee.town,
                'contact_phone_number': employee.contact_phone_number,
                'alternate_phone_number': employee.alternate_phone_number,
                'means_of_identification': employee.means_of_identification,
                'means_of_identification_number': employee.means_of_identification_number,
                'state_of_issuance': employee.state_of_issuance,
                'address_of_employee': employee.address_of_employee,
                'job_title': employee.job_title,
                'marital_status': employee.marital_status,
                'number_of_primary_dependants': employee.number_of_primary_dependants,
            })
        return res

    def action_save_info(self):
        if not self.employee_id:
            return
        values = {
            'identification_number': self.identification_number,
            'passport_number': self.passport_number,
            'birth_place': self.birth_place,
            'surname': self.surname,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth,
            'state_of_origin': self.state_of_origin,
            'lga': self.lga,
            'town': self.town,
            'contact_phone_number': self.contact_phone_number,
            'alternate_phone_number': self.alternate_phone_number,
            'means_of_identification': self.means_of_identification,
            'means_of_identification_number': self.means_of_identification_number,
            'state_of_issuance': self.state_of_issuance,
            'address_of_employee': self.address_of_employee,
            'job_title': self.job_title,
            'marital_status': self.marital_status,
            'number_of_primary_dependants': self.number_of_primary_dependants,
        }
        self.employee_id.write(values)
