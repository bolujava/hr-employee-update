
from odoo import models, fields, api
import logging


logger = logging.getLogger(__name__)
class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    # Fields
    training_id = fields.Many2one('training.list', string="Training Program")
    training_id_in_planning = fields.Many2one(
        'training.request',
        string='Course Title',
        domain=lambda self: self._get_current_user_employee()
    )
    reference_id = fields.Char(
        string='Training Reference',
        compute='_compute_reference_id',
        store=True,
        readonly=True
    )
    progress_percentage = fields.Float(
        string="Progress (%)",
        default=0.0,
        tracking=True
    )
    training_progress = fields.Selection(
        [
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        ],
        string="Training Progress",
        default='not_started',
        tracking=True
    )
    assessment_score = fields.Float(
        string="Assessment Score (%)",
        default=0.0,
        tracking=True,
        help="Assessment score percentage (0-100)"
    )


    @api.model
    def _get_current_user_employee(self):
        """Dynamic domain to filter training requests by the current user's linked employee and active records."""
        user = self.env.user
        employee = user.employee_id
        domain = [('employee_id.user_id', '=', user.id), ('state', '=', 'line_manager')]
        if employee and employee.department_id:
            domain.append(('department_id', '=', employee.department_id.id))
        logger.info(f"Domain for training_id_in_planning: {domain}")
        # Log the training requests that match the domain
        training_requests = self.env['training.request'].search(domain)
        logger.info(f"Training requests matching the domain: {training_requests}")

        return domain

    @api.depends('training_id_in_planning')
    def _compute_reference_id(self):
        """Automatically populate the reference field when training is selected."""
        for record in self:
            record.reference_id = record.training_id_in_planning.reference_id if record.training_id_in_planning else False


    @api.onchange('progress_percentage')
    def _onchange_progress_percentage(self):
        """Update the progress status based on progress percentage."""
        for record in self:
            if record.progress_percentage >= 100.0:
                record.progress_percentage = 100.0  # Prevent over 100%
                record.training_progress = 'completed'
            elif 0 < record.progress_percentage < 100:
                record.training_progress = 'in_progress'
            else:
                record.training_progress = 'not_started'

    def _sync_training_request(self):
        """Sync progress data from PlanningSlot to the linked Training Request."""
        for record in self:
            try:
                if record.training_id_in_planning:
                    record.training_id_in_planning.write({
                        'progress_percentage': record.progress_percentage,
                        'training_progress': record.training_progress,
                        'assessment_score': record.assessment_score
                    })
            except Exception as e:
                logger.error(f"Failed to sync training request: {str(e)}")
                raise

    @api.model
    def create(self, vals):
        record = super(PlanningSlot, self).create(vals)
        if 'progress_percentage' in vals or 'assessment_score' in vals:
            record._sync_training_request()
        return record

    def write(self, vals):
        result = super(PlanningSlot, self).write(vals)
        if 'progress_percentage' in vals or 'assessment_score' in vals:
            self._sync_training_request()
        return result

    @api.constrains('progress_percentage', 'assessment_score')
    def _check_values(self):
        for record in self:
            if not 0 <= record.progress_percentage <= 100:
                raise ValidationError("Progress must be 0-100%")
            if not 0 <= record.assessment_score <= 100:
                raise ValidationError("Assessment score must be 0-100%")