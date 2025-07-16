from odoo import models, fields, api
from datetime import datetime, timedelta


class RoyceStockPickingExtension(models.Model):
    _inherit = 'stock.picking'

    # Track if SMS notifications have been sent to avoid duplicates
    royce_delivery_scheduled_sms_sent = fields.Boolean('Delivery Scheduled SMS Sent', default=False)
    royce_goods_shipped_sms_sent = fields.Boolean('Goods Shipped SMS Sent', default=False)
    royce_delivery_completed_sms_sent = fields.Boolean('Delivery Completed SMS Sent', default=False)
    royce_delivery_delayed_sms_sent = fields.Boolean('Delivery Delayed SMS Sent', default=False)

    def action_assign(self):
        """Override action_assign to trigger delivery scheduled notification"""
        result = super().action_assign()
        
        # Trigger SMS notification for delivery scheduled
        for picking in self:
            if (picking.picking_type_id.code == 'outgoing' and 
                not picking.royce_delivery_scheduled_sms_sent and 
                picking.partner_id and 
                picking.sale_id):
                self._trigger_delivery_scheduled_notification(picking)
                picking.royce_delivery_scheduled_sms_sent = True
        
        return result

    def button_validate(self):
        """Override button_validate to trigger goods shipped notification"""
        result = super().button_validate()
        
        # Trigger SMS notification for goods shipped/delivery completed
        for picking in self:
            if (picking.picking_type_id.code == 'outgoing' and 
                picking.state == 'done' and 
                picking.partner_id and 
                picking.sale_id):
                
                # Check if this is shipping or final delivery
                if picking._is_final_delivery():
                    if not picking.royce_delivery_completed_sms_sent:
                        self._trigger_delivery_completed_notification(picking)
                        picking.royce_delivery_completed_sms_sent = True
                else:
                    if not picking.royce_goods_shipped_sms_sent:
                        self._trigger_goods_shipped_notification(picking)
                        picking.royce_goods_shipped_sms_sent = True
        
        return result

    def _is_final_delivery(self):
        """Check if this is the final delivery (goods reached customer)"""
        self.ensure_one()
        # Simple logic: if delivery is to customer location, it's final delivery
        # You can customize this logic based on your business process
        return (self.location_dest_id.usage == 'customer' or 
                'customer' in self.location_dest_id.name.lower())

    def _trigger_delivery_scheduled_notification(self, picking):
        """Trigger SMS notification for delivery scheduled"""
        # Calculate delivery date (scheduled date or estimated)
        delivery_date = picking.scheduled_date or (datetime.now() + timedelta(days=1))
        
        # Get order information
        order = picking.sale_id
        salesperson = order.user_id.name if order and order.user_id else 'Sales Team'
        
        context_data = {
            'customer_name': picking.partner_id.name,
            'customer_id': picking.partner_id.id,
            'order_number': order.name if order else picking.name,
            'tracking_number': picking.name,
            'delivery_date': delivery_date.strftime('%Y-%m-%d'),
            'expected_date': delivery_date.strftime('%Y-%m-%d'),
            'salesperson_name': salesperson,
            'delivery_address': self._get_delivery_address(picking),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'stock.picking',
            'related_record_id': picking.id,
            'related_record_name': picking.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='delivery_scheduled',
            context_data=context_data,
            trigger_user_id=picking.create_uid.id if picking.create_uid else self.env.user.id
        )

    def _trigger_goods_shipped_notification(self, picking):
        """Trigger SMS notification for goods shipped"""
        # Calculate expected delivery date
        expected_delivery = picking.scheduled_date or (datetime.now() + timedelta(days=2))
        
        # Get order information
        order = picking.sale_id
        salesperson = order.user_id.name if order and order.user_id else 'Sales Team'
        
        context_data = {
            'customer_name': picking.partner_id.name,
            'customer_id': picking.partner_id.id,
            'order_number': order.name if order else picking.name,
            'tracking_number': picking.name,
            'delivery_date': expected_delivery.strftime('%Y-%m-%d'),
            'expected_date': expected_delivery.strftime('%Y-%m-%d'),
            'salesperson_name': salesperson,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'stock.picking',
            'related_record_id': picking.id,
            'related_record_name': picking.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='goods_shipped',
            context_data=context_data,
            trigger_user_id=picking.create_uid.id if picking.create_uid else self.env.user.id
        )

    def _trigger_delivery_completed_notification(self, picking):
        """Trigger SMS notification for delivery completed"""
        # Get order information
        order = picking.sale_id
        salesperson = order.user_id.name if order and order.user_id else 'Sales Team'
        
        context_data = {
            'customer_name': picking.partner_id.name,
            'customer_id': picking.partner_id.id,
            'order_number': order.name if order else picking.name,
            'tracking_number': picking.name,
            'delivery_date': datetime.now().strftime('%Y-%m-%d'),
            'salesperson_name': salesperson,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'stock.picking',
            'related_record_id': picking.id,
            'related_record_name': picking.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='delivery_completed',
            context_data=context_data,
            trigger_user_id=picking.create_uid.id if picking.create_uid else self.env.user.id
        )

    def _trigger_delivery_delayed_notification(self, picking, delay_reason=''):
        """Trigger SMS notification for delivery delayed"""
        # Calculate new expected date
        new_expected_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Get order information
        order = picking.sale_id
        salesperson = order.user_id.name if order and order.user_id else 'Sales Team'
        
        context_data = {
            'customer_name': picking.partner_id.name,
            'customer_id': picking.partner_id.id,
            'order_number': order.name if order else picking.name,
            'tracking_number': picking.name,
            'expected_date': new_expected_date,
            'delivery_date': new_expected_date,
            'salesperson_name': salesperson,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'stock.picking',
            'related_record_id': picking.id,
            'related_record_name': picking.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='delivery_delayed',
            context_data=context_data,
            trigger_user_id=picking.create_uid.id if picking.create_uid else self.env.user.id
        )

    def _get_delivery_address(self, picking):
        """Get formatted delivery address"""
        partner = picking.partner_id
        address_parts = []
        
        if partner.street:
            address_parts.append(partner.street)
        if partner.city:
            address_parts.append(partner.city)
        
        return ', '.join(address_parts) if address_parts else 'Delivery Address'

    @api.model
    def _check_delayed_deliveries(self):
        """Scheduled action to check for delayed deliveries"""
        from datetime import date
        
        # Find pickings that are overdue
        delayed_pickings = self.search([
            ('picking_type_id.code', '=', 'outgoing'),
            ('state', 'not in', ['done', 'cancel']),
            ('scheduled_date', '<', datetime.now()),
            ('royce_delivery_delayed_sms_sent', '=', False),
            ('sale_id', '!=', False),  # Only sales orders
        ])
        
        for picking in delayed_pickings:
            # Check if delay is significant (more than 1 day)
            if picking.scheduled_date:
                delay_hours = (datetime.now() - picking.scheduled_date).total_seconds() / 3600
                if delay_hours > 24:  # More than 24 hours delay
                    self._trigger_delivery_delayed_notification(picking)
                    picking.royce_delivery_delayed_sms_sent = True

    def action_manual_delivery_delay_notification(self):
        """Manual action to send delivery delay notification"""
        self.ensure_one()
        if not self.royce_delivery_delayed_sms_sent:
            self._trigger_delivery_delayed_notification(self, 'Manual notification')
            self.royce_delivery_delayed_sms_sent = True
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Delivery Delay Notification Sent',
                    'message': f'Delay notification sent for {self.name}',
                    'type': 'success',
                    'sticky': False,
                }
            }