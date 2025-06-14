# -*- coding: utf-8 -*-
{
    'name': "Training_Management",

    'summary': """
        Training Management Module""",

    'description': """
       Employee can enrol from catalog of courses and keep track of their trainings
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','mail','web','web_cohort','approvals','planning','calendar'],

    # always loaded
    'data': [
        'security/training_request_rules.xml',
        'security/ir.model.access.csv',
        'data/mail_subtypes.xml',
        'data/email_templates.xml',
        'views/views.xml',
        'views/report_templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}