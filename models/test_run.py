from odoo import models, fields, exceptions
import requests

class TestRun(models.Model):
    _name = 'test.run'
    _description = 'Test Run'

    name = fields.Char(string="Name", required=True)
    _inherit = ['mail.thread', 'mail.activity.mixin']
        
    name = fields.Char(string="Nom", required=True)
    description = fields.Text(string="Description")

    
    test_case_id = fields.Many2one('test.case',string="Cas de test",required=True )

    project_id = fields.Many2one(related='test_case_id.project_id',store=True,string="Projet")
    tache_id = fields.Many2one('project.task', string="Tâche")

    tester_id = fields.Many2one('res.users',string="Testeur",default=lambda self: self.env.user)

    date = fields.Datetime(string="Date d'exécution",default=fields.Datetime.now)
    

    state = fields.Selection([('draft', 'Brouillon'),('running', 'En cours'),('done', 'Terminé') ], default='draft', tracking=True)

    result = fields.Selection([ ('pass', 'Passé'), ('fail', 'Échoué'),('blocked', 'Bloqué')], string="Résultat global", tracking=True)

    step_ids = fields.One2many('test.run.step','test_run_id',string="Étapes exécutées")
    
    
    # bouton démarrer
    #def action_start(self):
    #    self.state = 'running'
    def action_start(self):
        # Configuration Jenkins
        jenkins_url = "http://localhost:8080/job/tester_automate/buildWithParameters"
        user = "admin"
        # Ton jeton API que tu viens de générer
        api_token = "114911bcee26867f8fafe7c6805fd529c0" 
        # Le jeton de projet défini dans la config du job Jenkins (Build Triggers)
        token_projet = "SUPER_CLE" 

        for record in self:
            # On prépare l'ID pour l'envoyer à Jenkins
            params = {
                'token': token_projet,
                'ODOO_ID': str(record.id)
            }
            
            try:
                # Appel à l'API Jenkins avec authentification Basic
                response = requests.post(jenkins_url, params=params, auth=(user, api_token))
                
                if response.status_code in [200, 201, 202]:
                    # On change l'état dans Odoo pour montrer que c'est lancé
                    record.write({'state': 'running'})
                else:
                    raise exceptions.ValidationError(f"Erreur Jenkins ({response.status_code}) : {response.text}")
            except Exception as e:
                raise exceptions.ValidationError(f"Connexion Jenkins échouée : {str(e)}")

    # bouton terminer
    # Dans la classe TestRun (test.py)
    def action_done(self):
        for record in self:
            record.write({'state': 'done'})
            # Ce bloc fait le lien automatique
            if record.test_case_id:
                record.test_case_id.write({'state': 'done'})
            return True  
          