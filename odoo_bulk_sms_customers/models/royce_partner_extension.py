from odoo import models, fields, api
from datetime import datetime


class RoycePartnerExtension(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger SMS notifications for new customers/suppliers"""
        partners = super().create(vals_list)
        
        for partner in partners:
            # Check if new customer
            if partner.customer_rank > 0:
                self._trigger_customer_created_notification(partner)
            
            # Check if new supplier
            if partner.supplier_rank > 0:
                self._trigger_supplier_created_notification(partner)
        
        return partners

    def write(self, vals):
        """Override write to trigger SMS notifications for customer updates"""
        result = super().write(vals)
        
        # Check if customer information was updated
        if self.customer_rank > 0 and any(field in vals for field in ['name', 'phone', 'mobile', 'email', 'street']):
            for partner in self:
                self._trigger_customer_updated_notification(partner)
        
        return result

    def _trigger_customer_created_notification(self, partner):
        """Trigger SMS notification for new customer created"""
        context_data = {
            'customer_name': partner.name,
            'customer_id': partner.id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'res.partner',
            'related_record_id': partner.id,
            'related_record_name': partner.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='customer_created',
            context_data=context_data,
            trigger_user_id=self.env.user.id
        )

    def _trigger_supplier_created_notification(self, partner):
        """Trigger SMS notification for new supplier created"""
        context_data = {
            'supplier_name': partner.name,
            'supplier_id': partner.id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'res.partner',
            'related_record_id': partner.id,
            'related_record_name': partner.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='supplier_created',
            context_data=context_data,
            trigger_user_id=self.env.user.id
        )

    def _trigger_customer_updated_notification(self, partner):
        """Trigger SMS notification for customer info updated"""
        context_data = {
            'customer_name': partner.name,
            'customer_id': partner.id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'res.partner',
            'related_record_id': partner.id,
            'related_record_name': partner.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='customer_updated',
            context_data=context_data,
            trigger_user_id=self.env.user.id
        )
