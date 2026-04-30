from odoo import models, fields, exceptions, _
import requests

class TestRun(models.Model):
    _name = 'test.run'
    _description = 'Test Run'
    _inherit = ['mail.thread', 'mail.activity.mixin']
        
    name = fields.Char(string="Nom", required=True, tracking=True)
    description = fields.Text(string="Description")

    # Relation vers le Cas de Test (contient le nom du Job Jenkins)[cite: 1]
    test_case_id = fields.Many2one('test.case', string="Cas de test", required=True)

    project_id = fields.Many2one(related='test_case_id.project_id', store=True, string="Projet")
    tache_id = fields.Many2one('project.task', string="Tâche")

    tester_id = fields.Many2one('res.users', string="Testeur", default=lambda self: self.env.user)
    date = fields.Datetime(string="Date d'exécution", default=fields.Datetime.now)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('running', 'En cours'),
        ('done', 'Terminé')
    ], default='draft', tracking=True)

    result = fields.Selection([
        ('pass', 'Passé'),
        ('fail', 'Échoué'),
        ('blocked', 'Bloqué')
    ], string="Résultat global", tracking=True)

    step_ids = fields.One2many('test.run.step', 'test_run_id', string="Étapes exécutées")
    
    def action_start(self):
        """
        Lance le job Jenkins en utilisant les paramètres saisis manuellement 
        dans la configuration et le test case.
        """
        # 1. Récupérer la configuration globale active
        config = self.env['jenkins.config'].get_active_config()
        
        user = config.jenkins_user
        api_token = config.jenkins_token
        base_url = config.jenkins_url.rstrip('/')

        for record in self:
            # 2. Récupérer le nom du job saisi dans le Test Case associé
            job_name = record.test_case_id.jenkins_job_name
            
            if not job_name:
                raise exceptions.ValidationError(_(
                    "Le nom du job Jenkins n'est pas saisi dans le Cas de Test associé."
                ))

            # 3. Construire l'URL dynamiquement avec le nom du job
            # On utilise /build car le pipeline est géré par le Jenkinsfile
            jenkins_url = f"{base_url}/job/{job_name}/build"
            
            # Paramètres envoyés à Jenkins (optionnel, pour suivi)
            params = {
                'ODOO_TEST_RUN_ID': str(record.id)
            }
            
            try:
                # 4. Appel à l'API Jenkins avec authentification Basic
                response = requests.post(
                    jenkins_url, 
                    params=params, 
                    auth=(user, api_token),
                    timeout=15
                )
                
                # Codes 200, 201 ou 202 signifient que Jenkins a accepté la demande
                if response.status_code in [200, 201, 202]:
                    record.write({'state': 'running'})
                    record.message_post(body=_(f"Job Jenkins '{job_name}' lancé avec succès."))
                else:
                    raise exceptions.ValidationError(_(
                        f"Erreur Jenkins ({response.status_code}) : {response.text}"
                    ))
            except Exception as e:
                raise exceptions.ValidationError(_(f"Connexion Jenkins échouée : {str(e)}"))

    def action_done(self):
        """Bouton terminer : passe à l'état terminé et ferme le test case."""
        for record in self:
            record.write({'state': 'done'})
            if record.test_case_id:
                record.test_case_id.write({'state': 'done'})
        return True