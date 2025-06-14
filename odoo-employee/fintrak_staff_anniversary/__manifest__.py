{
    'name': 'FINTRAK Staff Anniversary',
    'version': '1.0',
    'category': 'Human Resources',
    'author':'LOTUS BETA ANALYTICS NIGERIA',
    'summary': 'Send Congratulatory Emails on Work Anniversary',
    'depends': ['hr', 'mail'],
    'data': [
        'data/anniversary_email_template.xml',
        'data/cron_job.xml',
        'views/hr_employee_view.xml',
    ],
    'installable': True,
}
