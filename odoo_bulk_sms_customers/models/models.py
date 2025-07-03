# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class odoo_bulk_sms_customers(models.Model):
#     _name = 'odoo_bulk_sms_customers.odoo_bulk_sms_customers'
#     _description = 'odoo_bulk_sms_customers.odoo_bulk_sms_customers'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

