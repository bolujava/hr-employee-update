from odoo import models, fields, api
from datetime import datetime

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    join_date = fields.Date(string="Join Date")

    @api.model
    def send_anniversary_email(self):
        today = datetime.today()
        employees = self.search([('join_date', '!=', False)])
        for employee in employees:
            if (
                employee.join_date and
                employee.join_date.month == today.month and
                employee.join_date.day == today.day
            ):
                template = self.env.ref('fintrak_staff_anniversary.email_template_work_anniversary')
                if template:
                    template.send_mail(employee.id, force_send=True)
