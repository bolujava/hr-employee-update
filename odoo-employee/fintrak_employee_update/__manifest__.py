# -*- coding: utf-8 -*-
{
    'name': "fintrak_employee_update",

    'summary': """
        Employee Update
    """,

    'description': """
        Employee Update
    """,

    'author': "Lotus Beta Analytics",
    'website': "https://www.lotusbetaanalytics.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr',],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'security/ir.rule.xml',
        'views/views.xml',
        'views/public_views.xml',
        # 'views/personal_info.xml',
        'views/employee_personal_info_wizard.xml',
        # 'views/actions.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
}
