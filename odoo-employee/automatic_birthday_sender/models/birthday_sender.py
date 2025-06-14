from odoo import models, fields, api
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class BirthdaySender(models.Model):
    _inherit = 'hr.employee'

    def send_birthday_wishes(self):
        """
        Send birthday emails to employees celebrating today
        using the specified template with explicit recipient handling.
        """
        try:
            _logger.info("Birthday job started...")
            today = date.today()
            _logger.info("Today's date: %s", today.strftime('%Y-%m-%d'))

            # Find all active employees with birthdays and valid emails
            all_employees = self.search([
                ('birthday', '!=', False),
                ('active', '=', True),
                ('work_email', '!=', False),
                ('work_email', '!=', ''),
            ])

            # Log all employees being checked (for debugging)
            for emp in all_employees:
                _logger.info("Checking employee: %s | Birthday: %s", emp.name, emp.birthday)

            # Filter employees with today's birthday
            birthday_employees = all_employees.filtered(
                lambda emp: emp.birthday and
                            emp.birthday.month == today.month and
                            emp.birthday.day == today.day
            )

            _logger.info("Found %d employee(s) with birthday today.", len(birthday_employees))

            # Log birthday matches
            for emp in birthday_employees:
                _logger.info("Birthday match: %s | Email: %s", emp.name, emp.work_email)

            if not birthday_employees:
                return True

            # Get the email template
            template = self.env.ref('automatic_birthday_sender.mail_template_employee_birthday')

            # Send emails with explicit recipient handling
            for employee in birthday_employees:
                try:
                    # Create mail values with explicit recipient
                    mail_values = {
                        'email_to': employee.work_email,
                        'model': 'hr.employee',
                        'res_id': employee.id,
                        'email_from': self.env.company.email or self.env.user.email,
                    }

                    # Send with force_send to ensure immediate delivery
                    template.send_mail(
                        employee.id,
                        email_values=mail_values,
                        force_send=True
                    )
                    _logger.info("Birthday email sent to %s (%s)", employee.name, employee.work_email)
                except Exception as e:
                    _logger.error("Failed to send to %s: %s", employee.name, str(e))

            return True
        except Exception as e:
            _logger.error("Birthday notification error: %s", str(e))
            return False