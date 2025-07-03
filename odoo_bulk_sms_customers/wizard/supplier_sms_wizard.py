from odoo import models, fields, api
from odoo.exceptions import UserError


class SupplierSmsWizard(models.TransientModel):
    _name = 'supplier.sms.wizard'
    _description = 'Send SMS to Suppliers Wizard'

    selection_type = fields.Selection([
        ('all', 'All Suppliers'),
        ('selected', 'Selected Suppliers'),
        ('category', 'By Category'),
    ], 'Send To', default='all', required=True)
    
    supplier_ids = fields.Many2many(
        'res.partner', 
        string='Select Suppliers',
        domain=[('supplier_rank', '>', 0)]
    )
    category_ids = fields.Many2many('res.partner.category', string='Supplier Categories')
    template_id = fields.Many2one('royce.sms.royce.template', 'SMS Template')
    custom_message = fields.Text('Custom Message')
    message_preview = fields.Text('Message Preview', readonly=True)
    
    # Statistics
    total_suppliers = fields.Integer('Total Suppliers', compute='_compute_statistics')
    suppliers_with_phone = fields.Integer('Suppliers with Phone', compute='_compute_statistics')

    @api.depends('selection_type', 'supplier_ids', 'category_ids')
    def _compute_statistics(self):
        for wizard in self:
            if wizard.selection_type == 'all':
                suppliers = self.env['res.partner'].search([
                    ('supplier_rank', '>', 0)
                ])
            elif wizard.selection_type == 'selected':
                suppliers = wizard.supplier_ids
            else:  # category
                if wizard.category_ids:
                    suppliers = self.env['res.partner'].search([
                        ('supplier_rank', '>', 0),
                        ('category_id', 'in', wizard.category_ids.ids)
                    ])
                else:
                    suppliers = self.env['res.partner']
            
            wizard.total_suppliers = len(suppliers)
            suppliers_with_phone = suppliers.filtered(lambda s: s.mobile or s.phone)
            wizard.suppliers_with_phone = len(suppliers_with_phone)

    @api.onchange('template_id', 'custom_message')
    def _onchange_message(self):
        """Update message preview"""
        if self.template_id:
            sample_record = type('obj', (object,), {'name': 'XYZ Suppliers Ltd'})
            self.message_preview = self.template_id.render_template(self.template_id.body, sample_record)
        else:
            self.message_preview = self.custom_message or ''

    def send_sms(self):
        """Send SMS to suppliers"""
        # Validate message
        if not self.template_id and not self.custom_message:
            raise UserError('Please select a template or enter a custom message.')

        # Get suppliers based on selection
        if self.selection_type == 'all':
            suppliers = self.env['res.partner'].search([
                ('supplier_rank', '>', 0)
            ])
        elif self.selection_type == 'selected':
            if not self.supplier_ids:
                raise UserError('Please select at least one supplier.')
            suppliers = self.supplier_ids
        else:  # category
            if not self.category_ids:
                raise UserError('Please select at least one category.')
            suppliers = self.env['res.partner'].search([
                ('supplier_rank', '>', 0),
                ('category_id', 'in', self.category_ids.ids)
            ])

        # Filter suppliers with phone numbers
        valid_suppliers = suppliers.filtered(lambda s: s.mobile or s.phone)
        
        if not valid_suppliers:
            raise UserError('No suppliers found with phone numbers.')

        # Send SMS to each supplier using existing sms.log
        success_count = 0
        failed_count = 0
        sms_log = self.env['royce.sms.log']
        customer_sms_log = self.env['customer.sms.log']

        for supplier in valid_suppliers:
            # Prepare message
            if self.template_id:
                message = self.template_id.render_template(self.template_id.body, supplier)
            else:
                message = self.custom_message

            # Send SMS using existing sms.log method
            result = sms_log.send_sms(
                phone_number=supplier.mobile or supplier.phone,
                message=message,
                recipient_name=supplier.name,
                template_id=self.template_id.id if self.template_id else None,
                recipient_type='supplier',
                recipient_id=supplier.id
            )

            # Create supplier-specific log
            customer_sms_log.log_customer_sms(
                partner_id=supplier.id,
                message=message,
                template_id=self.template_id.id if self.template_id else None,
                partner_type='supplier',
                sms_log_id=result.get('log_id'),
                status='sent' if result['success'] else 'failed',
                error_message=result.get('error') if not result['success'] else None
            )

            if result['success']:
                success_count += 1
            else:
                failed_count += 1

        # Show result
        message = f"Supplier SMS sending completed!\nSuccess: {success_count}\nFailed: {failed_count}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'SMS Sent to Suppliers',
                'message': message,
                'type': 'success' if failed_count == 0 else 'warning',
                'sticky': False,
            }
        }