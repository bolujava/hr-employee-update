# -*- coding: utf-8 -*-
# from odoo import http


# class RefundRequest(http.Controller):
#     @http.route('/refund_request/refund_request', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/refund_request/refund_request/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('refund_request.listing', {
#             'root': '/refund_request/refund_request',
#             'objects': http.request.env['refund_request.refund_request'].search([]),
#         })

#     @http.route('/refund_request/refund_request/objects/<model("refund_request.refund_request"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('refund_request.object', {
#             'object': obj
#         })
