from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, ondelete="cascade")
    identification_number = fields.Char()
    passport_number = fields.Char()
    birth_place = fields.Char()
    surname = fields.Char("Surname")
    first_name = fields.Char("First Name")
    middle_name = fields.Char("Middle Name")
    gender = fields.Selection([('male', 'Male'),
                               ('female', 'Female'),
                               ('other', 'Other'), ], string='Gender', groups=False)
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

    def create(self, vals):
        employee = super(HrEmployeePublic, self).create(vals)
        if employee.user_id:
            employee.user_id.groups_id = [(4, self.env.ref('fintrak_employee_update.group_employee_self_service').id)]
        return employee




