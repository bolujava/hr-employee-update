{
    'name': 'Employee Laptop Allocation',
    'version': '1.0',
    'category': 'Human Resources',
    'depends': ['hr', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/laptop_allocation_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
