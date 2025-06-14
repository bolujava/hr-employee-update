from odoo import models, fields, tools, api
from odoo.exceptions import ValidationError


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # Basic identification fields
    user_id = fields.Many2one('res.users', string="Related User", store=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, ondelete="cascade")

    is_logged_in_user = fields.Boolean(compute='_compute_is_logged_in_user')

    @api.depends('user_id')
    def _compute_is_logged_in_user(self):
        current_user = self.env.uid
        for rec in self:
            rec.is_logged_in_user = rec.user_id.id == current_user

    # Personal information fields
    identification_number = fields.Char(string="Identification Number")
    passport_number = fields.Char()
    birth_place = fields.Char()
    surname = fields.Char("Surname")
    first_name = fields.Char("First Name")
    middle_name = fields.Char("Middle Name")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', groups=False)
    date_of_birth = fields.Date(string="Date of Birth")
    state_of_origin = fields.Char(string="State of Origin")
    lga = fields.Char(string="LGA")
    town = fields.Char(string="Town")

    # Contact information
    contact_phone_number = fields.Char(string="Contact Phone Number")
    alternate_phone_number = fields.Char(string="Alternate Phone Number")

    # Identification fields
    means_of_identification = fields.Selection([
        ('nin', 'NIN'),
        ('passport', 'Passport'),
        ('driver_license', 'Driver\'s License'),
        ('voter_card', 'Voter\'s Card'),
        ('other', 'Other')
    ], string="Means of Identification")
    means_of_identification_number = fields.Char(string="Identification Number")
    state_of_issuance = fields.Char(string="State of Issuance")

    # Address information
    address_of_employee = fields.Text(string="Address of Employee")

    # Job information
    job_title = fields.Char(string="Job Title")

    # Family information
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed')
    ], string="Marital Status")
    number_of_primary_dependants = fields.Integer(string="Number of Primary Dependants")

    @api.model
    def _get_fields(self):
        """Override to include user_id and other custom fields in the view"""
        # Get standard fields from parent
        standard_fields = super()._get_fields()

        # Split and safely remove 'emp.id'
        standard_fields_list = [f.strip() for f in standard_fields.split(',')]
        standard_fields_list = [f for f in standard_fields_list if f != 'emp.id']

        # List of additional fields to include
        additional_fields = [
            'emp.user_id',
            'emp.employee_id',
            'emp.identification_number',
            'emp.passport_number',
            'emp.birth_place',
            'emp.surname',
            'emp.first_name',
            'emp.middle_name',
            'emp.gender',
            'emp.date_of_birth',
            'emp.state_of_origin',
            'emp.lga',
            'emp.town',
            'emp.contact_phone_number',
            'emp.alternate_phone_number',
            'emp.means_of_identification',
            'emp.means_of_identification_number',
            'emp.state_of_issuance',
            'emp.address_of_employee',
            'emp.job_title',
            'emp.marital_status',
            'emp.number_of_primary_dependants'
        ]

        # Add additional fields if not already present
        for field in additional_fields:
            if field not in standard_fields_list:
                standard_fields_list.append(field)

        return ', '.join(standard_fields_list)

    def init(self):
        """Initialize or update the database view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        fields_definition = self._get_fields()
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT 
                    emp.id as id,
                    {fields_definition}
                FROM hr_employee emp
                WHERE emp.active IS TRUE
            )
        """)
        self.pool.clear_caches()

    @api.model
    def _update_existing_records(self):
        """Set user_id on existing records"""
        for public_emp in self.search([('user_id', '=', False)]):
            if public_emp.employee_id.user_id:
                public_emp.write({
                    'user_id': public_emp.employee_id.user_id.id
                })

    @api.constrains('user_id', 'employee_id')
    def _check_user_employee_consistency(self):
        """Ensure user_id matches employee's user_id"""
        for record in self:
            if record.user_id and record.employee_id.user_id != record.user_id:
                raise ValidationError("User ID must match the employee's user ID")

    def action_open_wizard(self):
        """Open the personal info wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fill Personal Info',
            'res_model': 'employee.personal.info.wizard',
            'view_mode': 'form',
            'target': 'new',
            'domain': [('employee_id', '=', self.id)],
            'view_id': self.env.ref('lotus_beta_employee_update.view_employee_personal_info_wizard_form').id,
            'context': {
                'default_employee_id': self.id,
            },
        }
