from odoo import models, fields, api
import re


class RoyceSmsNotificationTemplate(models.Model):
    _name = 'royce.sms.notification.template'
    _description = 'Royce SMS Notification Template'
    _order = 'template_category, event_type, name'

    name = fields.Char('Template Name', required=True)
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
    
    message_body = fields.Text('Message Body', required=True, 
                              help='Use variables like ${customer_name}, ${amount}, ${order_number}, ${date}, ${company_name}')
    active = fields.Boolean('Active', default=True, 
                           help='Inactive templates will not trigger notifications')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    
    # Preview field
    preview_text = fields.Text('Preview', compute='_compute_preview', 
                              help='Preview with sample data')

    @api.depends('message_body')
    def _compute_preview_old(self):
        """Generate preview with sample data"""
        sample_data = {
            'customer_name': 'ABC Company Ltd',
            'supplier_name': 'XYZ Suppliers Ltd',
            'amount': '1,500.00',
            'order_number': 'SO001',
            'invoice_number': 'INV001',
            'date': '2024-12-24',
            'company_name': 'Roycelt Ltd',
            'payment_amount': '1,200.00',
            'days_overdue': '5'
        }
        
        for template in self:
            if template.message_body:
                preview = template.message_body
                for key, value in sample_data.items():
                    preview = preview.replace(f'${{{key}}}', str(value))
                template.preview_text = preview
            else:
                template.preview_text = ''
    @api.depends('message_body')
    def _compute_preview(self):
        """Generate preview with sample data"""
        for template in self:
            if template.message_body:
                # Simple preview without complex processing
                template.preview_text = template.message_body.replace('${customer_name}', 'ABC Company Ltd').replace('${amount}', '1,500.00')
            else:
                template.preview_text = 'No message content'

    @api.model
    def render_template(self, template_body, context_data):
        """Render template with actual data"""
        if not template_body:
            return ''
        
        rendered_message = template_body
        for key, value in context_data.items():
            if value is not None:
                rendered_message = rendered_message.replace(f'${{{key}}}', str(value))
        
        return rendered_message

    @api.model
    def get_active_template(self, event_type, template_category):
        """Get active template for specific event and category"""
        template = self.search([
            ('event_type', '=', event_type),
            ('template_category', '=', template_category),
            ('active', '=', True)
        ], limit=1)
        return template

    @api.constrains('event_type', 'template_category', 'active')
    def _check_unique_active_template(self):
        """Ensure only one active template per event type and category"""
        for record in self:
            if record.active:
                existing = self.search([
                    ('event_type', '=', record.event_type),
                    ('template_category', '=', record.template_category),
                    ('active', '=', True),
                    ('id', '!=', record.id),
                    ('company_id', '=', record.company_id.id)
                ])
                if existing:
                    from odoo.exceptions import ValidationError
                    raise ValidationError(
                        f'Only one active template allowed per event type and category. '
                        f'Conflict with: {existing[0].name}'
                    )