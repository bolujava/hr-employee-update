from odoo import models, fields, api
from odoo.exceptions import UserError


class RefundRequest(models.Model):
    _name = 'refund_request.refund_request'
    _description = 'Refund Request'

    reason = fields.Selection([
        ('my_flight_was_cancelled', 'My flight was cancelled'),
        ('my_flight_was_delayed', 'My flight was delayed'),
        ('my_flight_was_rescheduled', 'My flight was rescheduled'),
        ('unable_to_make_flight', 'I am / was unable to make the flight / I changed my mind')
    ], string="What is your request")

    name = fields.Char(string="Name on Ticket")
    reference_code = fields.Char(string="Booking Reference Code", required=True)
    date_of_sale = fields.Date(string="Date of Ticket Sale", required=True)
    ticket_number = fields.Char(string="Ticket Number", required=True)
    amount = fields.Float(string="Amount", required=True)
    phone_number = fields.Char(string="Phone Number")
    email = fields.Char(string="Email")
    account_name = fields.Char(string="Account Name")
    account_number = fields.Char(string="Account Number")
    receiving_bank = fields.Char(string="Receiving Bank")
    evidence = fields.Binary(string="Upload Evidence")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('inpayment', 'In Payment'),
    ], string='Status', 
    default='draft', tracking=True)

    assigned_support_id = fields.Many2one(
        'res.users', 
        string='Assigned Support',
        domain=lambda self: [('groups_id', 'in', self.env.ref('una_refund_request.group_crm_support').id)],
        help="Assign this refund request to a CRM support officer."
    )

    @api.onchange('assigned_support_id')
    def _onchange_assigned_support(self):
        if self.assigned_support_id and self.assigned_support_id.email:
            mail_values = {
                'subject': f"Refund Request Assigned: {self.name}",
                'email_to': self.assigned_support_id.email,
                'body_html': f"<p>You have been assigned a new refund request: {self.reference_code}</p>",
            }
            self.env['mail.mail'].create(mail_values).send()


    def action_validate(self):
        if not self.env.user.has_group('una_refund_request.group_refund_officer'):
            raise UserError("Only Refund Officers can validate requests.")
        self.write({'state': 'valid'})

    def action_invalidate(self):
        if not self.env.user.has_group('una_refund_request.group_refund_officer'):
            raise UserError("Only Refund Officers can invalidate requests.")
        self.write({'state': 'invalid'})

    def action_approve_payment(self):
        if not self.env.user.has_group('una_refund_request.group_account_officer'):
            raise UserError("Only Account Officers can approve payments.")
        self.write({'state': 'inpayment'})

    def action_assign_support(self):
        if not self.env.user.has_group('una_refund_request.group_crm_lead'):
            raise UserError("Only CRM Leads can assign support tickets.")
        if not self.assigned_support_id:
            raise UserError("Please select a support officer to assign.")
        # Send internal notification (optional)
        self.message_post(
            body=f"The refund request has been assigned to {self.assigned_support_id.name}.",
            partner_ids=[self.assigned_support_id.partner_id.id]
        )