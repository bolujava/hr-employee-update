from odoo import models, fields, api
from odoo.exceptions import UserError

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    def send_disengagement_email(self):
        mail_server = self.env['ir.mail_server'].search([], limit=1)
        if not mail_server:
            raise UserError("No outgoing mail server configured.")

        for emp in self:
            if not emp.work_email:
                continue

            body = f"""
Dear {emp.name},

We hope this message finds you well.

We would like to formally notify you of your disengagement from the organization. This decision was not made lightly and follows careful consideration.

If you have any questions or require further clarification, please do not hesitate to reach out to the HR department.

We appreciate your contributions and wish you the very best in your future endeavors.

Kind regards,  
Human Resources
"""

            self.env['mail.mail'].create({
                'subject': 'Disengagement Notice',
                'body_html': f'<pre>{body}</pre>',
                'email_to': emp.work_email,
            }).send()
