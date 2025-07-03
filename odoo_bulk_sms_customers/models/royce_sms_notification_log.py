from odoo import models, fields, api
from datetime import datetime


class RoyceSmsNotificationLog(models.Model):
    _name = 'royce.sms.notification.log'
    _description = 'Royce SMS Notification Log'
    _order = 'create_date desc'

    name = fields.Char('Reference', required=True)
    event_type = fields.Selection([
        ('customer_created', 'New Customer Created'),
        ('customer_updated', 'Customer Info Updated'),
        ('invoice_generated', 'Invoice Generated'),
        ('payment_received', 'Payment Received'),
        ('invoice_overdue', 'Invoice Overdue'),
        ('supplier_created', 'New Supplier Created'),
        ('purchase_order_created', 'Purchase Order Created'),
        ('payment_made_supplier', 'Payment Made to Supplier'),
    ], 'Event Type', required=True)
    
    template_category = fields.Selection([
        ('customer_facing', 'Customer Facing'),
        ('internal_notification', 'Internal Notification'),
    ], 'Template Category', required=True)
    
    recipient_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('internal_user', 'Internal User'),
        ('company_phone', 'Company Phone'),
    ], 'Recipient Type', required=True)
    
    recipient_name = fields.Char('Recipient Name')
    recipient_phone = fields.Char('Recipient Phone')
    message_sent = fields.Text('Message Sent')
    
    # Related record information
    related_model = fields.Char('Related Model')
    related_record_id = fields.Integer('Related Record ID')
    related_record_name = fields.Char('Related Record Name')
    
    # SMS sending information
    template_id = fields.Many2one('royce.sms.notification.template', 'Template Used')
    sms_log_id = fields.Many2one('sms.log', 'SMS Log Reference')
    status = fields.Selection([
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], 'Status', required=True)
    error_message = fields.Text('Error Message')
    
    trigger_user_id = fields.Many2one('res.users', 'Triggered By')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.model
    def create_notification_log(self, event_type, template_category, recipient_type, 
                               recipient_name, recipient_phone, message, template_id,
                               related_model=None, related_record_id=None, related_record_name=None,
                               trigger_user_id=None, sms_log_id=None, status='sent', error_message=None):
        """Create notification log entry"""
        
        log_vals = {
            'name': f"ROYCE-SMS-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'event_type': event_type,
            'template_category': template_category,
            'recipient_type': recipient_type,
            'recipient_name': recipient_name,
            'recipient_phone': recipient_phone,
            'message_sent': message,
            'related_model': related_model,
            'related_record_id': related_record_id,
            'related_record_name': related_record_name,
            'template_id': template_id,
            'sms_log_id': sms_log_id,
            'status': status,
            'error_message': error_message,
            'trigger_user_id': trigger_user_id,
        }
        
        return self.create(log_vals)