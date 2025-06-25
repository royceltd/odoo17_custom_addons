# ====================================================================================
# FILE: wizard/sms_unified_wizard.py
# ====================================================================================
from odoo import models, fields, api
from odoo.exceptions import UserError


class SmsUnifiedWizard(models.TransientModel):
    _name = 'sms.unified.wizard'
    _description = 'Send SMS - Unified Wizard'

    # Step 1: Choose recipient type
    recipient_type = fields.Selection([
        ('contacts', 'Contacts'),
        ('employees', 'Employees'),
    ], 'Send To', default='contacts', required=True)
    
    # Step 2: Choose selection method
    selection_type = fields.Selection([
        ('all', 'All'),
        ('selected', 'Selected'),
    ], 'Selection Method', default='all', required=True)
    
    # Step 3: Select specific recipients
    contact_ids = fields.Many2many('res.partner', string='Select Contacts')
    employee_ids = fields.Many2many('hr.employee', string='Select Employees')
    
    # Message configuration
    template_id = fields.Many2one('sms.royce.template', 'SMS Template')
    custom_message = fields.Text('Custom Message')
    message_preview = fields.Text('Message Preview', readonly=True)
    
    # Statistics
    total_recipients = fields.Integer('Total Recipients', compute='_compute_statistics')
    recipients_with_phone = fields.Integer('Recipients with Phone', compute='_compute_statistics')

    @api.depends('recipient_type', 'selection_type', 'contact_ids', 'employee_ids')
    def _compute_statistics(self):
        for wizard in self:
            if wizard.recipient_type == 'contacts':
                if wizard.selection_type == 'all':
                    all_recipients = self.env['res.partner'].search([('is_company', '=', False)])
                else:
                    all_recipients = wizard.contact_ids
                
                recipients_with_phone = all_recipients.filtered(lambda c: c.mobile or c.phone)
                
            else:  # employees
                if wizard.selection_type == 'all':
                    all_recipients = self.env['hr.employee'].search([])
                else:
                    all_recipients = wizard.employee_ids
                
                recipients_with_phone = all_recipients.filtered(lambda e: e.mobile_phone or e.work_phone)
            
            wizard.total_recipients = len(all_recipients)
            wizard.recipients_with_phone = len(recipients_with_phone)

    @api.onchange('recipient_type', 'selection_type')
    def _onchange_recipient_selection(self):
        """Clear selections when changing recipient type"""
        if self.recipient_type == 'contacts':
            self.employee_ids = [(5, 0, 0)]  # Clear employees
        else:
            self.contact_ids = [(5, 0, 0)]   # Clear contacts

    @api.onchange('template_id', 'custom_message')
    def _onchange_message(self):
        """Update message preview"""
        if self.template_id:
            # Show preview with sample name
            sample_record = type('obj', (object,), {'name': 'John Doe'})
            self.message_preview = self.template_id.render_template(self.template_id.body, sample_record)
        else:
            self.message_preview = self.custom_message or ''

    def send_sms(self):
        """Send SMS to selected recipients"""
        # Validate message
        if not self.template_id and not self.custom_message:
            raise UserError('Please select a template or enter a custom message.')

        # Get recipients based on selection
        if self.recipient_type == 'contacts':
            if self.selection_type == 'all':
                recipients = self.env['res.partner'].search([('is_company', '=', False)])
            else:
                if not self.contact_ids:
                    raise UserError('Please select at least one contact.')
                recipients = self.contact_ids
            
            # Filter contacts with phone numbers
            valid_recipients = recipients.filtered(lambda c: c.mobile or c.phone)
            recipient_type_name = 'contact'
            
        else:  # employees
            if self.selection_type == 'all':
                recipients = self.env['hr.employee'].search([])
            else:
                if not self.employee_ids:
                    raise UserError('Please select at least one employee.')
                recipients = self.employee_ids
            
            # Filter employees with phone numbers
            valid_recipients = recipients.filtered(lambda e: e.mobile_phone or e.work_phone)
            recipient_type_name = 'employee'

        if not valid_recipients:
            raise UserError(f'No {self.recipient_type} found with phone numbers.')

        # Send SMS to each recipient
        success_count = 0
        failed_count = 0
        sms_log = self.env['sms.log']

        for recipient in valid_recipients:
            # Get phone number based on recipient type
            if self.recipient_type == 'contacts':
                phone = recipient.mobile or recipient.phone
            else:  # employees
                phone = recipient.mobile_phone or recipient.work_phone
            
            # Prepare message
            if self.template_id:
                message = self.template_id.render_template(self.template_id.body, recipient)
            else:
                message = self.custom_message

            # Send SMS
            result = sms_log.send_sms(
                phone_number=phone,
                message=message,
                recipient_name=recipient.name,
                template_id=self.template_id.id if self.template_id else None,
                recipient_type=recipient_type_name,
                recipient_id=recipient.id
            )

            if result['success']:
                success_count += 1
            else:
                failed_count += 1

        # Show result
        message = f"SMS sending completed!\nSuccess: {success_count}\nFailed: {failed_count}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'SMS Sent',
                'message': message,
                'type': 'success' if failed_count == 0 else 'warning',
                'sticky': False,
            }
        }

    def action_refresh_statistics(self):
        """Refresh statistics manually"""
        self._compute_statistics()
        return True
        return {'type': 'ir.actions.do_nothing'}