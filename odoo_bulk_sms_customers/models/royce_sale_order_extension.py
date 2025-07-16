from odoo import models, fields, api
from datetime import datetime, timedelta


class RoyceSaleOrderExtension(models.Model):
    _inherit = 'sale.order'

    # Track if SMS notifications have been sent to avoid duplicates
    royce_quotation_sms_sent = fields.Boolean('Quotation SMS Sent', default=False)
    royce_order_sms_sent = fields.Boolean('Order Confirmation SMS Sent', default=False)

    def write(self, vals):
        """Override write to detect state changes and email sending"""
        result = super().write(vals)
        
        # Check if quotation state changed to 'sent' (when email is sent)
        if 'state' in vals and vals['state'] == 'sent':
            for order in self:
                if not order.royce_quotation_sms_sent and order.partner_id:
                    self._trigger_quotation_sent_notification(order)
                    order.royce_quotation_sms_sent = True
        
        return result

    def action_quotation_sent(self):
        """Override quotation sent to trigger SMS notification"""
        result = super().action_quotation_sent()
        
        # Trigger SMS notification for quotation sent
        for order in self:
            if not order.royce_quotation_sms_sent and order.partner_id:
                self._trigger_quotation_sent_notification(order)
                order.royce_quotation_sms_sent = True
        
        return result

    def action_confirm(self):
        """Override order confirmation to trigger SMS notification"""
        result = super().action_confirm()
        
        # Trigger SMS notification for order confirmed
        for order in self:
            if not order.royce_order_sms_sent and order.partner_id:
                self._trigger_sale_order_confirmed_notification(order)
                order.royce_order_sms_sent = True
        
        return result

    # Add this new method to handle email composer
    @api.model
    def _message_post_after_hook(self, message, msg_vals):
        """Hook after message post (when email is sent)"""
        result = super()._message_post_after_hook(message, msg_vals)
        
        # Check if this is a quotation email being sent
        if (self.state == 'draft' and 
            msg_vals.get('email_from') and 
            not self.royce_quotation_sms_sent and 
            self.partner_id):
            
            self._trigger_quotation_sent_notification(self)
            self.royce_quotation_sms_sent = True
        
        return result

    def _trigger_quotation_sent_notification(self, order):
        """Trigger SMS notification for quotation sent"""
        # Calculate validity date (usually 30 days from now)
        validity_date = order.validity_date or (datetime.now().date() + timedelta(days=30))
        
        # Get salesperson name
        salesperson = order.user_id.name if order.user_id else 'Sales Team'
        
        context_data = {
            'customer_name': order.partner_id.name,
            'customer_id': order.partner_id.id,
            'quote_number': order.name,
            'order_number': order.name,
            'amount': f"{order.amount_total:,.2f}",
            'delivery_date': validity_date.strftime('%Y-%m-%d'),
            'salesperson_name': salesperson,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'sale.order',
            'related_record_id': order.id,
            'related_record_name': order.name,
        }
        
        # Add debug print
        print(f"DEBUG: Sending quotation SMS for {order.name} to {order.partner_id.name}")
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='quotation_sent',
            context_data=context_data,
            trigger_user_id=order.user_id.id if order.user_id else self.env.user.id
        )

    def _trigger_sale_order_confirmed_notification(self, order):
        """Trigger SMS notification for sales order confirmed"""
        # Calculate expected delivery date
        expected_delivery = order.commitment_date or (datetime.now().date() + timedelta(days=7))
        
        # Get salesperson name
        salesperson = order.user_id.name if order.user_id else 'Sales Team'
        
        context_data = {
            'customer_name': order.partner_id.name,
            'customer_id': order.partner_id.id,
            'order_number': order.name,
            'quote_number': order.name,
            'amount': f"{order.amount_total:,.2f}",
            'delivery_date': expected_delivery.strftime('%Y-%m-%d'),
            'expected_date': expected_delivery.strftime('%Y-%m-%d'),
            'salesperson_name': salesperson,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'sale.order',
            'related_record_id': order.id,
            'related_record_name': order.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='sale_order_confirmed',
            context_data=context_data,
            trigger_user_id=order.user_id.id if order.user_id else self.env.user.id
        )