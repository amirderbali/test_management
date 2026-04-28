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
    
    @api.model_create_multi
    def create(self, vals_list):
        # Création normale des étapes
        steps = super(TestRunStep, self).create(vals_list)
        
        for step in steps:
            # Si l'étape est en échec, on crée le bug automatiquement
            if step.state == 'fail':
                self.env['test.bug'].create({
                    'name': f"Bug - {step.test_run_id.name or 'Sans nom'}",
                    'project_id': step.test_run_id.project_id.id,
                    'test_run_id': step.test_run_id.id,
                    'description': f"Échec de l'étape : {step.description}\nRésultat réel : {step.actual_result}",
                })
        return steps

