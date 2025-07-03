from odoo import models, fields, api
from odoo.exceptions import UserError


class CustomerSmsWizard(models.TransientModel):
    _name = 'customer.sms.wizard'
    _description = 'Send SMS to Customers Wizard'

    selection_type = fields.Selection([
        ('all', 'All Customers'),
        ('selected', 'Selected Customers'),
        ('category', 'By Category'),
    ], 'Send To', default='all', required=True)
    
    customer_ids = fields.Many2many(
        'res.partner', 
        string='Select Customers',
        domain=[('customer_rank', '>', 0)]
    )
    category_ids = fields.Many2many('res.partner.category', string='Customer Categories')
    template_id = fields.Many2one('royce.sms.royce.template', 'SMS Template')
    custom_message = fields.Text('Custom Message')
    message_preview = fields.Text('Message Preview', readonly=True)
    
    # Statistics
    total_customers = fields.Integer('Total Customers', compute='_compute_statistics')
    customers_with_phone = fields.Integer('Customers with Phone', compute='_compute_statistics')

    @api.depends('selection_type', 'customer_ids', 'category_ids')
    def _compute_statistics(self):
        for wizard in self:
            if wizard.selection_type == 'all':
                customers = self.env['res.partner'].search([
                    ('customer_rank', '>', 0)
                ])
            elif wizard.selection_type == 'selected':
                customers = wizard.customer_ids
            else:  # category
                if wizard.category_ids:
                    customers = self.env['res.partner'].search([
                        ('customer_rank', '>', 0),
                        ('category_id', 'in', wizard.category_ids.ids)
                    ])
                else:
                    customers = self.env['res.partner']
            
            wizard.total_customers = len(customers)
            customers_with_phone = customers.filtered(lambda c: c.mobile or c.phone)
            wizard.customers_with_phone = len(customers_with_phone)

    @api.onchange('template_id', 'custom_message')
    def _onchange_message(self):
        """Update message preview"""
        if self.template_id:
            sample_record = type('obj', (object,), {'name': 'ABC Company Ltd'})
            self.message_preview = self.template_id.render_template(self.template_id.body, sample_record)
        else:
            self.message_preview = self.custom_message or ''

    def send_sms(self):
        """Send SMS to customers"""
        # Validate message
        if not self.template_id and not self.custom_message:
            raise UserError('Please select a template or enter a custom message.')

        # Get customers based on selection
        if self.selection_type == 'all':
            customers = self.env['res.partner'].search([
                ('customer_rank', '>', 0)
            ])
        elif self.selection_type == 'selected':
            if not self.customer_ids:
                raise UserError('Please select at least one customer.')
            customers = self.customer_ids
        else:  # category
            if not self.category_ids:
                raise UserError('Please select at least one category.')
            customers = self.env['res.partner'].search([
                ('customer_rank', '>', 0),
                ('category_id', 'in', self.category_ids.ids)
            ])

        # Filter customers with phone numbers
        valid_customers = customers.filtered(lambda c: c.mobile or c.phone)
        
        if not valid_customers:
            raise UserError('No customers found with phone numbers.')

        # Send SMS to each customer using existing sms.log
        success_count = 0
        failed_count = 0
        sms_log = self.env['royce.sms.log']
        customer_sms_log = self.env['customer.sms.log']

        for customer in valid_customers:
            # Prepare message
            if self.template_id:
                message = self.template_id.render_template(self.template_id.body, customer)
            else:
                message = self.custom_message

            # Send SMS using existing sms.log method
            result = sms_log.send_sms(
                phone_number=customer.mobile or customer.phone,
                message=message,
                recipient_name=customer.name,
                template_id=self.template_id.id if self.template_id else None,
                recipient_type='customer',
                recipient_id=customer.id
            )

            # Create customer-specific log
            customer_sms_log.log_customer_sms(
                partner_id=customer.id,
                message=message,
                template_id=self.template_id.id if self.template_id else None,
                partner_type='customer',
                sms_log_id=result.get('log_id'),
                status='sent' if result['success'] else 'failed',
                error_message=result.get('error') if not result['success'] else None
            )

            if result['success']:
                success_count += 1
            else:
                failed_count += 1

        # Show result
        message = f"Customer SMS sending completed!\nSuccess: {success_count}\nFailed: {failed_count}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'SMS Sent to Customers',
                'message': message,
                'type': 'success' if failed_count == 0 else 'warning',
                'sticky': False,
            }
        }
