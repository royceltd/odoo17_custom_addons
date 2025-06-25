from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SmsConfig(models.Model):
    _name = 'sms.config'
    _description = 'SMS Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Add this line
    _rec_name = 'name'

    name = fields.Char('Configuration Name', required=True, default='SMS Configuration')
    api_key = fields.Char('API Key', required=True, help='Bearer token for SMS API authentication')
    sender_id = fields.Char('Sender ID', required=True, help='SMS sender identification')
    api_url = fields.Char('API URL', required=True, default='https://roycebulksms.com/api/sendmessage')
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.constrains('active')
    def _check_active_config(self):
        """Ensure only one active configuration per company"""
        for record in self:
            if record.active:
                existing = self.search([
                    ('active', '=', True),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError('Only one SMS configuration can be active per company.')

    @api.model
    def get_active_config(self):
        """Get the active SMS configuration"""
        config = self.search([('active', '=', True), ('company_id', '=', self.env.company.id)], limit=1)
        if not config:
            raise ValidationError('No active SMS configuration found. Please configure SMS settings first.')
        return config