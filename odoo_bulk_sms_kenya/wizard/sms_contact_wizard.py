from odoo import models, fields, api
from odoo.exceptions import UserError


class SmsContactWizard(models.TransientModel):
    _name = 'sms.contact.wizard'
    _description = 'Send SMS to Contacts Wizard'

    selection_type = fields.Selection([
        ('all', 'All Contacts'),
        ('selected', 'Selected Contacts'),
    ], 'Send To', default='all', required=True)
    
    contact_ids = fields.Many2many('res.partner', string='Select Contacts')
    template_id = fields.Many2one('sms.template', 'SMS Template')
    custom_message = fields.Text('Custom Message')
    message_preview = fields.Text('Message Preview', readonly=True)
    
    # Statistics
    total_contacts = fields.Integer('Total Contacts', compute='_compute_statistics')
    contacts_with_phone = fields.Integer('Contacts with Phone', compute='_compute_statistics')

    @api.depends('selection_type', 'contact_ids')
    def _compute_statistics(self):
        for wizard in self:
            if wizard.selection_type == 'all':
                all_contacts = self.env['res.partner'].search([('is_company', '=', False)])
            else:
                all_contacts = wizard.contact_ids
            
            wizard.total_contacts = len(all_contacts)
            
            contacts_with_phone = all_contacts.filtered(
                lambda c: c.mobile or c.phone
            )
            wizard.contacts_with_phone = len(contacts_with_phone)

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
        """Send SMS to contacts"""
        # Validate message
        if not self.template_id and not self.custom_message:
            raise UserError('Please select a template or enter a custom message.')

        # Get contacts
        if self.selection_type == 'all':
            contacts = self.env['res.partner'].search([('is_company', '=', False)])
        else:
            if not self.contact_ids:
                raise UserError('Please select at least one contact.')
            contacts = self.contact_ids

        # Filter contacts with phone numbers
        valid_contacts = contacts.filtered(lambda c: c.mobile or c.phone)
        
        if not valid_contacts:
            raise UserError('No contacts found with phone numbers.')

        # Send SMS to each contact
        success_count = 0
        failed_count = 0
        sms_log = self.env['sms.log']

        for contact in valid_contacts:
            # Get phone number (prefer mobile over phone)
            phone = contact.mobile or contact.phone
            
            # Prepare message
            if self.template_id:
                message = self.template_id.render_template(self.template_id.body, contact)
            else:
                message = self.custom_message

            # Send SMS
            result = sms_log.send_sms(
                phone_number=phone,
                message=message,
                recipient_name=contact.name,
                template_id=self.template_id.id if self.template_id else None,
                recipient_type='contact',
                recipient_id=contact.id
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

