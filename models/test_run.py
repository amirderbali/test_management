from odoo import models, fields, exceptions, _
from odoo.exceptions import UserError
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
     Remplace l'ancienne version. 
     Délègue l'exécution technique au Test Case associé.
     """
     self.ensure_one()
    
    # 1. Vérification de sécurité
     if not self.test_case_id:
      raise UserError(_("Aucun Cas de Test n'est associé à ce run."))
    
    # 2. On vérifie si le job est prêt côté Jenkins
     if self.test_case_id.jenkins_job_status != 'created':
        raise UserError(_(
            "Le job Jenkins n'a pas encore été configuré ou créé pour ce cas de test. "
            "Veuillez cliquer sur 'Créer Job Jenkins' dans le formulaire du Cas de Test."
        ))

    # 3. Appel de la méthode centralisée dans test_case_jenkins.py
    # On passe l'ID du run actuel pour le suivi
     self.test_case_id.action_run_jenkins(run_id=self.id)

    # 4. Mise à jour de l'état du run local
     self.write({
        'state': 'running', # ou 'in_progress' selon votre workflow
    })
    
     return True
    def action_done(self):
        """Bouton terminer : passe à l'état terminé et ferme le test case."""
        for record in self:
            record.write({'state': 'done'})
            if record.test_case_id:
                record.test_case_id.write({'state': 'done'})
        return True
    def action_auto_resolve_bugs(self, step_description=None):
     """
    Appelé par Jenkins via RPC.
    Cherche les bugs liés à ce Run et les passe en 'Résolu'.
    """
     self.ensure_one()
    
    # On cherche les bugs liés à ce Run qui ne sont pas fermés
     domain = [
        ('test_run_id', '=', self.id),
        ('state', 'not in', ['resolved', 'closed'])
     ]
    
    # Optionnel : Si Jenkins envoie la description de l'étape, on filtre
     if step_description:
        # On cherche le bug dont la description contient le nom de l'étape
        domain.append(('description', 'ilike', step_description))
    
     bugs = self.env['test.bug'].search(domain)
    
     if bugs:
        bugs.write({'state': 'resolved'})
        for bug in bugs:
            bug.message_post(body="✅ Résolution automatique : Le test associé est désormais 'Passé' sur Jenkins.")
     return True