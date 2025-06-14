{
    'name': 'Employee Birthday Notifications',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Automated birthday emails for employees',
    'description': """
Sends automatic birthday emails to employees
==========================================
- Daily cron checks for birthdays
- Sends emails to employees
- Creates calendar events
    """,
    'depends': ['hr', 'mail'],  # Removed 'calendar' and 'web_gantt' since we removed calendar functionality
    'data': [
        'data/hr_birthday_data.xml',       # Cron job definition
        'data/mail_template_data.xml',     # Email template
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}