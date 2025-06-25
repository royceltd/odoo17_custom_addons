from odoo import models, fields, api
import re


class SmsTemplate(models.Model):
    _name = 'sms.royce.template'
    _description = 'SMS Template'
    _order = 'name'

    name = fields.Char('Template Name', required=True)
    subject = fields.Char('Subject')
    body = fields.Text('Message Body', required=True, help='Use ${name} for dynamic name field')
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.model
    def render_template(self, template_body, record):
        """Render template with dynamic values"""
        if not template_body:
            return ''
        
        # Replace ${name} with actual name
        name = record.name if hasattr(record, 'name') else str(record)
        rendered_body = template_body.replace('${name}', name or '')
        
        return rendered_body

    def preview_template(self, record_name='John Doe'):
        """Preview template with sample data"""
        self.ensure_one()
        sample_record = type('obj', (object,), {'name': record_name})
        return self.render_template(self.body, sample_record)