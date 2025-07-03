from odoo import models, fields, api
from datetime import datetime


class RoyceInvoiceExtension(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger SMS notifications for new invoices"""
        moves = super().create(vals_list)
        
        for move in moves:
            # Check if it's a customer invoice
            if move.move_type == 'out_invoice' and move.partner_id.customer_rank > 0:
                self._trigger_invoice_generated_notification(move)
        
        return moves

    def action_post(self):
        """Override action_post to trigger notification when invoice is confirmed"""
        result = super().action_post()
        
        for move in self:
            if move.move_type == 'out_invoice' and move.partner_id.customer_rank > 0:
                self._trigger_invoice_generated_notification(move)
        
        return result

    def _trigger_invoice_generated_notification(self, invoice):
        """Trigger SMS notification for invoice generated"""
        context_data = {
            'customer_name': invoice.partner_id.name,
            'customer_id': invoice.partner_id.id,
            'invoice_number': invoice.name,
            'amount': f"{invoice.amount_total:,.2f}",
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'account.move',
            'related_record_id': invoice.id,
            'related_record_name': invoice.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='invoice_generated',
            context_data=context_data,
            trigger_user_id=invoice.create_uid.id if invoice.create_uid else self.env.user.id
        )

    @api.model
    def _check_overdue_invoices(self):
        """Scheduled action to check for overdue invoices"""
        from datetime import date
        
        overdue_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'in_payment']),
            ('invoice_date_due', '<', date.today()),
            ('partner_id.customer_rank', '>', 0)
        ])
        
        for invoice in overdue_invoices:
            # Calculate days overdue
            days_overdue = (date.today() - invoice.invoice_date_due).days
            
            # Only send notification once per invoice (you might want to add a field to track this)
            if not hasattr(invoice, '_overdue_notification_sent'):
                self._trigger_invoice_overdue_notification(invoice, days_overdue)

    def _trigger_invoice_overdue_notification(self, invoice, days_overdue):
        """Trigger SMS notification for overdue invoice"""
        context_data = {
            'customer_name': invoice.partner_id.name,
            'customer_id': invoice.partner_id.id,
            'invoice_number': invoice.name,
            'amount': f"{invoice.amount_total:,.2f}",
            'days_overdue': str(days_overdue),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
            'related_model': 'account.move',
            'related_record_id': invoice.id,
            'related_record_name': invoice.name,
        }
        
        notification_service = self.env['royce.sms.notification.service']
        notification_service.send_notification(
            event_type='invoice_overdue',
            context_data=context_data,
            trigger_user_id=invoice.create_uid.id if invoice.create_uid else self.env.user.id
        )
