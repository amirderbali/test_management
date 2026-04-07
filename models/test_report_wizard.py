from odoo import models, fields, api
import datetime

class TestReportWizard(models.TransientModel):
    _name = 'test.report.wizard'
    _description = 'Assistant Rapport Test'

    project_id = fields.Many2one(
        'project.project',
        string='Projet',
        required=True  # obligatoire maintenant
    )
    date_debut = fields.Date(string='Date début')
    date_fin   = fields.Date(string='Date fin')

    def action_generate_report(self):
        return self.env.ref(
            'test_management.action_report_test_global'
        ).report_action(self)