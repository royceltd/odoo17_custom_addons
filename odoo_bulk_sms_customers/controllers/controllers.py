# -*- coding: utf-8 -*-
# from odoo import http


# class OdooBulkSmsCustomers(http.Controller):
#     @http.route('/odoo_bulk_sms_customers/odoo_bulk_sms_customers', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo_bulk_sms_customers/odoo_bulk_sms_customers/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo_bulk_sms_customers.listing', {
#             'root': '/odoo_bulk_sms_customers/odoo_bulk_sms_customers',
#             'objects': http.request.env['odoo_bulk_sms_customers.odoo_bulk_sms_customers'].search([]),
#         })

#     @http.route('/odoo_bulk_sms_customers/odoo_bulk_sms_customers/objects/<model("odoo_bulk_sms_customers.odoo_bulk_sms_customers"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo_bulk_sms_customers.object', {
#             'object': obj
#         })

