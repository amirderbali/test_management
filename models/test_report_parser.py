from odoo import models, api
import datetime

class TestReportParser(models.AbstractModel):
    _name = 'report.test_management.report_test_global_template'
    _description = 'Parser Rapport Test'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['test.report.wizard'].browse(docids)

        project = wizard.project_id

        # Domaines filtrés par projet
        domain_case = [('project_id', '=', project.id)]

        domain_run = [('project_id', '=', project.id)]
        if wizard.date_debut:
            domain_run.append(('date', '>=', wizard.date_debut))
        if wizard.date_fin:
            domain_run.append(('date', '<=', wizard.date_fin))

        domain_bug = [('project_id', '=', project.id)]
        if wizard.date_debut:
            domain_bug.append(('create_date', '>=', wizard.date_debut))
        if wizard.date_fin:
            domain_bug.append(('create_date', '<=', wizard.date_fin))

        test_cases = self.env['test.case'].search(domain_case)
        test_runs  = self.env['test.run'].search(domain_run)
        bugs       = self.env['test.bug'].search(domain_bug)

        return {
            'doc_ids'    : docids,
            'doc_model'  : 'test.report.wizard',
            'docs'       : wizard,
            'project'    : project,
            'test_cases' : test_cases,
            'test_runs'  : test_runs,
            'bugs'       : bugs,
            'now'        : datetime.datetime.now().strftime('%d/%m/%Y à %H:%M'),
        }