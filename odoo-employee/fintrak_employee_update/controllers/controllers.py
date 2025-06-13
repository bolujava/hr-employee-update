# -*- coding: utf-8 -*-
# from odoo import http


# class EmployeeUpdate(http.Controller):
#     @http.route('/employee_update/employee_update', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/employee_update/employee_update/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('employee_update.listing', {
#             'root': '/employee_update/employee_update',
#             'objects': http.request.env['employee_update.employee_update'].search([]),
#         })

#     @http.route('/employee_update/employee_update/objects/<model("employee_update.employee_update"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('employee_update.object', {
#             'object': obj
#         })
