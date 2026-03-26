from odoo import models,fields,api

class TestRunStep(models.Model) :
    _name = 'test.run.step'
    _description = 'Test Run Step'

    test_run_id = fields.Many2one( 'test.run',string="Test Run",ondelete='cascade')

    description = fields.Text(string="Description")

    expected_result = fields.Text(string="Résultat attendu")

    actual_result = fields.Text(string="Résultat réel")

    state = fields.Selection([ ('pass', 'Passé'),('fail', 'Échoué'),('blocked', 'Bloqué')], string="Résultat")
    
    bug_id = fields.Many2one('test.bug',string="Bug")
    
    
    def write(self, vals):
     result = super().write(vals)
     if 'state' in vals and vals['state'] == 'fail':
        for step in self:
            if not step.bug_id:
                bug = self.env['test.bug'].create({
                    'name': 'Bug - ' + (step.test_run_id.name or ''),
                    'project_id': step.test_run_id.project_id.id,
                    'test_run_id': step.test_run_id.id,
                    'description': step.actual_result,
                })
                step.bug_id = bug.id
        return result

