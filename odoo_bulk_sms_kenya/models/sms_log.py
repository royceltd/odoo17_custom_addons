from odoo import models, fields, api
import requests
import json
from datetime import datetime
import re


class SmsLog(models.Model):
    _name = 'sms.log'
    _description = 'SMS Log'
    _order = 'create_date desc'

    name = fields.Char('Reference', required=True)
    recipient_name = fields.Char('Recipient Name')
    phone_number = fields.Char('Phone Number', required=True)
    message = fields.Text('Message', required=True)
    sender_id = fields.Char('Sender ID')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    ], 'Status', default='draft')
    error_message = fields.Text('Error Message')
    sent_date = fields.Datetime('Sent Date')
    template_id = fields.Many2one('sms.royce.template', 'Template Used')
    recipient_type = fields.Selection([
        ('contact', 'Contact'),
        ('employee', 'Employee'),
        ('custom', 'Custom'),
    ], 'Recipient Type')
    recipient_id = fields.Integer('Recipient ID')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.model
    def send_sms(self, phone_number, message, recipient_name=None, template_id=None, recipient_type='custom', recipient_id=None):
        """Send SMS via API and log the attempt"""
        
        # Get active SMS configuration

        
        try:
            config = self.env['sms.config'].get_active_config()
            print(f"Using SMS Config: (ID: {config.id})")
        except Exception as e:
            print(f"Error fetching SMS config: {str(e)}")
            return {'success': False, 'error': str(e)}

        # Clean phone number
        clean_phone = self._clean_phone_number(phone_number)
        if not clean_phone:
            print("Invalid phone number format")
            return {'success': False, 'error': 'Invalid phone number'}
        else:
            print(f"Cleaned phone number: {clean_phone} ++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

        # Create log record
        log_vals = {
            'name': f"SMS-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'recipient_name': recipient_name,
            'phone_number': clean_phone,
            'message': message,
            'sender_id': config.sender_id,
            'template_id': template_id,
            'recipient_type': recipient_type,
            'recipient_id': recipient_id,
        }
        log_record = self.create(log_vals)

        print(f"Sending SMS to {clean_phone} with message: {message}")

        # Prepare API request
        headers = {
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'phone_number': clean_phone,
            'text_message': message,
            'sender_id': config.sender_id
        }

        try:
            # Send SMS via API
            response = requests.post(config.api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                log_record.write({
                    'status': 'sent',
                    'sent_date': fields.Datetime.now()
                })
                print("send sms response: ", response.text)
                return {'success': True, 'log_id': log_record.id}
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                log_record.write({
                    'status': 'failed',
                    'error_message': error_msg
                })
                print(f"Failed to send SMS: {error_msg}")
                return {'success': False, 'error': error_msg, 'log_id': log_record.id}
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            error_msg = f"Request Error: {str(e)}"
            log_record.write({
                'status': 'failed',
                'error_message': error_msg
            })
            return {'success': False, 'error': error_msg, 'log_id': log_record.id}

    @api.model
    def _clean_phone_number(self, phone):
        """Clean and validate phone number"""
        if not phone:
            return None
            
        # Remove all non-digit characters
        clean = re.sub(r'\D', '', str(phone))
        
        # Handle Kenyan numbers
        if clean.startswith('0'):
            clean = '254' + clean[1:]  # Replace leading 0 with 254
        elif clean.startswith('254'):
            pass  # Already in correct format
        elif clean.startswith('7') and len(clean) == 9:
            clean = '254' + clean  # Add country code
        
        # Validate length (should be 12 digits for Kenya: 254XXXXXXXXX)
        if len(clean) == 12 and clean.startswith('254'):
            return clean
        
        return None

    def retry_send(self):
        """Retry sending failed SMS"""
        self.ensure_one()
        if self.status != 'failed':
            return {'warning': {'title': 'Warning', 'message': 'Can only retry failed messages'}}
        
        result = self.send_sms(
            self.phone_number,
            self.message,
            self.recipient_name,
            self.template_id.id if self.template_id else None,
            self.recipient_type,
            self.recipient_id
        )
        
        if result['success']:
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        else:
            return {'warning': {'title': 'Error', 'message': result['error']}}