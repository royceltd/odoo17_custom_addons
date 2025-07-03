from odoo import models, fields, api
from datetime import datetime, timedelta


class RoyceSmsNotificationService(models.Model):
    _name = 'royce.sms.notification.service'
    _description = 'Royce SMS Notification Service'

    @api.model
    def send_notification(self, event_type, context_data, trigger_user_id=None):
        """Main method to send SMS notifications for events"""
        
        # Get templates for this event
        template_model = self.env['royce.sms.notification.template']
        
        # Check for customer-facing template
        customer_template = template_model.get_active_template(event_type, 'customer_facing')
        
        # Check for internal template
        internal_template = template_model.get_active_template(event_type, 'internal_notification')
        
        results = []
        
        # Send customer-facing notification
        if customer_template:
            result = self._send_customer_facing_notification(
                customer_template, context_data, trigger_user_id
            )
            results.append(result)
        
        # Send internal notification
        if internal_template:
            result = self._send_internal_notification(
                internal_template, context_data, trigger_user_id
            )
            results.append(result)
        
        return results

    def _send_customer_facing_notification(self, template, context_data, trigger_user_id):
        """Send notification to customer/supplier"""
        
        # Get recipient based on event type
        recipient_phone = None
        recipient_name = None
        recipient_type = None
        
        if template.event_type in ['customer_created', 'customer_updated', 'invoice_generated', 
                                  'payment_received', 'invoice_overdue']:
            # Customer events
            if 'customer_id' in context_data:
                customer = self.env['res.partner'].browse(context_data['customer_id'])
                recipient_phone = customer.mobile or customer.phone
                recipient_name = customer.name
                recipient_type = 'customer'
        
        elif template.event_type in ['supplier_created', 'payment_made_supplier']:
            # Supplier events
            if 'supplier_id' in context_data:
                supplier = self.env['res.partner'].browse(context_data['supplier_id'])
                recipient_phone = supplier.mobile or supplier.phone
                recipient_name = supplier.name
                recipient_type = 'supplier'
        
        if not recipient_phone:
            return {'success': False, 'error': 'No recipient phone found'}
        
        # Render message
        message = template.render_template(template.message_body, context_data)
        
        # Send SMS
        return self._send_sms_and_log(
            template, message, recipient_name, recipient_phone, recipient_type,
            context_data, trigger_user_id
        )

    def _send_internal_notification(self, template, context_data, trigger_user_id):
        """Send notification to internal users"""
        
        recipients = []
        
        # Add person who created the record
        if trigger_user_id:
            user = self.env['res.users'].browse(trigger_user_id)
            if user.partner_id.mobile or user.partner_id.phone:
                recipients.append({
                    'name': user.name,
                    'phone': user.partner_id.mobile or user.partner_id.phone,
                    'type': 'internal_user'
                })
        
        # Add company phone for specific events
        if template.event_type in ['invoice_overdue', 'purchase_order_created']:
            company = self.env.company
            if company.phone:
                recipients.append({
                    'name': company.name,
                    'phone': company.phone,
                    'type': 'company_phone'
                })
        
        results = []
        for recipient in recipients:
            # Render message
            message = template.render_template(template.message_body, context_data)
            
            # Send SMS
            result = self._send_sms_and_log(
                template, message, recipient['name'], recipient['phone'], 
                recipient['type'], context_data, trigger_user_id
            )
            results.append(result)
        
        return results

    def _send_sms_and_log(self, template, message, recipient_name, recipient_phone, 
                         recipient_type, context_data, trigger_user_id):
        """Send SMS and create log entry"""
        
        # Send SMS using existing sms.log service
        sms_log = self.env['royce.sms.log']
        result = sms_log.send_sms(
            phone_number=recipient_phone,
            message=message,
            recipient_name=recipient_name,
            template_id=None,  # This is for royce templates, not sms.royce.template
            recipient_type='notification',
            recipient_id=context_data.get('related_record_id')
        )
        
        # Create notification log
        notification_log = self.env['royce.sms.notification.log']
        notification_log.create_notification_log(
            event_type=template.event_type,
            template_category=template.template_category,
            recipient_type=recipient_type,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            message=message,
            template_id=template.id,
            related_model=context_data.get('related_model'),
            related_record_id=context_data.get('related_record_id'),
            related_record_name=context_data.get('related_record_name'),
            trigger_user_id=trigger_user_id,
            sms_log_id=result.get('log_id'),
            status='sent' if result['success'] else 'failed',
            error_message=result.get('error')
        )
        
        return result