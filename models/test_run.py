from odoo import models, fields

class TestRun(models.Model):
    _name = 'test.run'
    _description = 'Test Run'

    name = fields.Char(string="Name", required=True)
    _inherit = ['mail.thread', 'mail.activity.mixin']
        
    name = fields.Char(string="Nom", required=True)
    description = fields.Text(string="Description")

    
    test_case_id = fields.Many2one('test.case',string="Cas de test",required=True )

    project_id = fields.Many2one(related='test_case_id.project_id',store=True,string="Projet")

    tester_id = fields.Many2one('res.users',string="Testeur",default=lambda self: self.env.user)

    date = fields.Datetime(string="Date d'exécution",default=fields.Datetime.now)
    

    state = fields.Selection([('draft', 'Brouillon'),('running', 'En cours'),('done', 'Terminé') ], default='draft', tracking=True)

    result = fields.Selection([ ('pass', 'Passé'), ('fail', 'Échoué'),('blocked', 'Bloqué')], string="Résultat global", tracking=True)

    step_ids = fields.One2many('test.run.step','test_run_id',string="Étapes exécutées")
    
    
    # bouton démarrer
    def action_start(self):
        self.state = 'running'

    # bouton terminer
    def action_done(self):
        self.state = 'done'
