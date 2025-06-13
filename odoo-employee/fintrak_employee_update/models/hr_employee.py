# models/hr_employee.py
from odoo import models, fields, tools, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee.public'

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

    def action_open_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fill Personal Info',
            'res_model': 'employee.personal.info.wizard',
            'view_mode': 'form',
            'target': 'new',
            'domain': [('employee_id', '=', self.id)],
            'view_id': self.env.ref('fintrak_employee_update.view_employee_personal_info_wizard_form').id,
            'context': {
                'default_employee_id': self.id,
            },
        }

    @api.model
    def _get_fields(self):
        # Exclude relational fields not suitable for a view
        return ',\n'.join('emp.%s' % name for name, field in self._fields.items()
                          if field.store and field.type not in ['one2many', 'many2many'])

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        fields_sql = self._get_fields()
        print("======= heleeee ========")
        print(fields_sql)
        print("======= heleeee ========")
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    {fields_sql}
                FROM hr_employee emp
                WHERE emp.active IS TRUE
            )
        """)