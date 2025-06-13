from importlib.metadata import requires

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    next_of_kin_name = fields.Char("Next of Kin")
    next_of_kin_address = fields.Char("Address of Next of Kin")
    next_of_kin_phone_number = fields.Char("Phone Number of Next of Kin")
    certificate_ids = fields.One2many('employee.certificate', 'employee_id')



class HrEmployeePublic(models.Model):
    _inherit ='hr.employee.public'

    next_of_kin_name = fields.Char("Next of Kin")
    next_of_kin_address = fields.Char("Address of Next of Kin")
    next_of_kin_phone_number = fields.Char("Phone Number of Next of Kin")


class EmployeeCertificate(models.Model):
    _name = 'employee.certificate'
    _descritption = 'Employee Certificate'

    name = fields.Char("Certificate Name", required=True)
    file = fields.Binary("Document", required=True, attachment=True)
    file_name = fields.Char("Name of file", required=True)
    employee_id = fields.Many2one('hr.employee', "Employee", required=True, ondelete='cascade')
    date_issued = fields.Date("Date Issued")
    date_of_expiration = fields.Date("Expiry Date")

    @api.constrains('date_issued','date_of_expiration')
    def _check_dates(self):
        for record in self:
            if record.date_issued and record.date_of_expiration:
                if record.date_issued > record.date_of_expiration:
                    raise ValidationError("Date Issued cannot be after Date of Expiration")

    def download_certificate(self):
        # This would normally be handled via attachment, not as a direct download
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/employee.certificate/{self.id}/file/{self.file_name}?download=true',
            'target': 'self',
        }

