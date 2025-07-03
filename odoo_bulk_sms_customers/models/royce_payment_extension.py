from odoo import models, fields, api
from datetime import datetime


class RoycePaymentExtension(models.Model):
    _inherit = 'account.payment'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger SMS notifications for payments"""
        payments = super().create(vals_list)
        
        for payment in payments:
            # Check if it's a customer payment (inbound)
            if payment.payment_type == 'inbound' and payment.partner_id.customer_rank > 0:
                self._trigger_payment_received_notification(payment)
            
            # Check if it's a supplier payment (outbound)
            elif payment.payment_type == 'outbound' and payment.partner_id.supplier_rank > 0:
                self._trigger_payment_made_supplier_notification(payment)
        
        return payments

    def action_post(self):
        """Override action_post to trigger notification when payment is confirmed"""
        result = super().action_post()
        
        for payment in self:
            if payment.payment_type == 'inbound' and payment.partner_id.customer_rank > 0:
                self._trigger_payment_received_notification(payment)
            elif payment.payment_type == 'outbound' and payment.partner_id.supplier_rank > 0:
                self._trigger_payment_made_supplier_notification(payment)
        
        return result

    def _trigger_payment_received_notification(self, payment):
        """Trigger SMS notification for payment received from customer"""
        context_data = {
            'customer_name': payment.partner_id.name,
            'customer_id': payment.partner_id.id,
            'payment_amount': f"{payment.amount:,.2f}",
            'amount': f"{payment.amount:,.2f}",
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'account.payment',
            'related_record_id': payment.id,
            'related_record_name': payment.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='payment_received',
            context_data=context_data,
            trigger_user_id=payment.create_uid.id if payment.create_uid else self.env.user.id
        )

    def _trigger_payment_made_supplier_notification(self, payment):
        """Trigger SMS notification for payment made to supplier"""
        context_data = {
            'supplier_name': payment.partner_id.name,
            'supplier_id': payment.partner_id.id,
            'payment_amount': f"{payment.amount:,.2f}",
            'amount': f"{payment.amount:,.2f}",
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'account.payment',
            'related_record_id': payment.id,
            'related_record_name': payment.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='payment_made_supplier',
            context_data=context_data,
            trigger_user_id=payment.create_uid.id if payment.create_uid else self.env.user.id
        )