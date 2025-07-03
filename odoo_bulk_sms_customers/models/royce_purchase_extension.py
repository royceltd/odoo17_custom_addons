from odoo import models, fields, api
from datetime import datetime


class RoycePurchaseExtension(models.Model):
    _inherit = 'purchase.order'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger SMS notifications for new purchase orders"""
        orders = super().create(vals_list)
        
        for order in orders:
            if order.partner_id.supplier_rank > 0:
                self._trigger_purchase_order_created_notification(order)
        
        return orders

    def button_confirm(self):
        """Override button_confirm to trigger notification when PO is confirmed"""
        result = super().button_confirm()
        
        for order in self:
            if order.partner_id.supplier_rank > 0:
                self._trigger_purchase_order_created_notification(order)
        
        return result

    def _trigger_purchase_order_created_notification(self, order):
        """Trigger SMS notification for purchase order created"""
        context_data = {
            'supplier_name': order.partner_id.name,
            'supplier_id': order.partner_id.id,
            'order_number': order.name,
            'amount': f"{order.amount_total:,.2f}",
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'purchase.order',
            'related_record_id': order.id,
            'related_record_name': order.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='purchase_order_created',
            context_data=context_data,
            trigger_user_id=order.create_uid.id if order.create_uid else self.env.user.id
        )