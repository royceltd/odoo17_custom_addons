from odoo import models, fields, api


class CustomerSmsLog(models.Model):
    _name = 'customer.sms.log'
    _description = 'Customer SMS Log'
    _order = 'create_date desc'
    _rec_name = 'reference'

    reference = fields.Char('Reference', required=True)
    partner_id = fields.Many2one('res.partner', 'Customer/Supplier', required=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    ], 'Type', required=True)
    phone_number = fields.Char('Phone Number', required=True)
    message = fields.Text('Message', required=True)
    template_id = fields.Many2one('royce.sms.royce.template', 'Template Used')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    ], 'Status', default='draft')
    error_message = fields.Text('Error Message')
    sent_date = fields.Datetime('Sent Date')
    sms_log_id = fields.Many2one('royce.sms.log', 'SMS Log Reference')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.model
    def log_customer_sms(self, partner_id, message, template_id=None, partner_type='customer', sms_log_id=None, status='sent', error_message=None):
        """Create customer SMS log entry (for tracking purposes only)"""
        partner = self.env['res.partner'].browse(partner_id)
        
        # Get phone number (prefer mobile over phone)
        phone = partner.mobile or partner.phone
        
        # Create customer SMS log
        log_vals = {
            'reference': f"CSMS-{fields.Datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'partner_id': partner.id,
            'partner_type': partner_type,
            'phone_number': phone,
            'message': message,
            'template_id': template_id,
            'status': status,
            'sms_log_id': sms_log_id,
            'error_message': error_message,
            'sent_date': fields.Datetime.now() if status == 'sent' else None,
        }
        
        return self.create(log_vals)

    def retry_send(self):
        """Retry sending failed SMS using main SMS log"""
        self.ensure_one()
        if self.status != 'failed':
            return {'warning': {'title': 'Warning', 'message': 'Can only retry failed messages'}}
        
        # Use existing sms.log.send_sms method
        sms_log = self.env['royce.sms.log']
        result = sms_log.send_sms(
            phone_number=self.phone_number,
            message=self.message,
            recipient_name=self.partner_id.name,
            template_id=self.template_id.id if self.template_id else None,
            recipient_type=self.partner_type,
            recipient_id=self.partner_id.id
        )
        
        # Update this customer log based on result
        if result['success']:
            self.write({
                'status': 'sent',
                'sent_date': fields.Datetime.now(),
                'sms_log_id': result.get('log_id'),
                'error_message': None
            })
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        else:
            self.write({
                'status': 'failed',
                'error_message': result.get('error', 'Unknown error')
            })
            return {'warning': {'title': 'Error', 'message': result['error']}}