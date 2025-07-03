from odoo import models, fields, api
from odoo.exceptions import UserError


class SmsEmployeeWizard(models.TransientModel):
    _name = 'royce.sms.employee.wizard'
    _description = 'Send SMS to Employees Wizard'

    selection_type = fields.Selection([
        ('all', 'All Employees'),
        ('selected', 'Selected Employees'),
    ], 'Send To', default='all', required=True)
    
    employee_ids = fields.Many2many('hr.employee', string='Select Employees')
    template_id = fields.Many2one('sms.template', 'SMS Template')
    custom_message = fields.Text('Custom Message')
    message_preview = fields.Text('Message Preview', readonly=True)
    
    # Statistics
    total_employees = fields.Integer('Total Employees', compute='_compute_statistics')
    employees_with_phone = fields.Integer('Employees with Phone', compute='_compute_statistics')

    @api.depends('selection_type', 'employee_ids')
    def _compute_statistics(self):
        for wizard in self:
            if wizard.selection_type == 'all':
                all_employees = self.env['hr.employee'].search([])
            else:
                all_employees = wizard.employee_ids
            
            wizard.total_employees = len(all_employees)
            
            employees_with_phone = all_employees.filtered(
                lambda e: e.mobile_phone or e.work_phone
            )
            wizard.employees_with_phone = len(employees_with_phone)

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
        """Send SMS to employees"""
        # Validate message
        if not self.template_id and not self.custom_message:
            raise UserError('Please select a template or enter a custom message.')

        # Get employees
        if self.selection_type == 'all':
            employees = self.env['hr.employee'].search([])
        else:
            if not self.employee_ids:
                raise UserError('Please select at least one employee.')
            employees = self.employee_ids

        # Filter employees with phone numbers
        valid_employees = employees.filtered(lambda e: e.mobile_phone or e.work_phone)
        
        if not valid_employees:
            raise UserError('No employees found with phone numbers.')

        # Send SMS to each employee
        success_count = 0
        failed_count = 0
        sms_log = self.env['sms.log']

        for employee in valid_employees:
            # Get phone number (prefer mobile over work phone)
            phone = employee.mobile_phone or employee.work_phone
            
            # Prepare message
            if self.template_id:
                message = self.template_id.render_template(self.template_id.body, employee)
            else:
                message = self.custom_message

            # Send SMS
            result = sms_log.send_sms(
                phone_number=phone,
                message=message,
                recipient_name=employee.name,
                template_id=self.template_id.id if self.template_id else None,
                recipient_type='employee',
                recipient_id=employee.id
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