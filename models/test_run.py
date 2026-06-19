from odoo import models, fields, api, _
from odoo.exceptions import UserError

class TestRun(models.Model):
    _name = 'test.run'
    _description = 'Test Run'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Nom", required=True, tracking=True)
    test_case_id = fields.Many2one('test.case', string="Cas de test", required=True)
    project_id = fields.Many2one(related='test_case_id.project_id', store=True, string="Projet")
    tache_id = fields.Many2one('project.task', string="Tâche")
    tester_id = fields.Many2one('res.users', string="Testeur", default=lambda self: self.env.user)
    date = fields.Datetime(string="Date d'exécution", default=fields.Datetime.now)
    description = fields.Text(string="Description")
    expected_result = fields.Text(string="Résultat attendu")

    # ✅ related pointe sur le bon champ : execution_mode (et non execution_type)
    execution_mode = fields.Selection(
        related='test_case_id.execution_mode',
        string="Mode d'exécution",
        store=True,
        readonly=True,
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('running', 'En cours'),
        ('done', 'Terminé'),
    ], default='draft', tracking=True)

    result = fields.Selection([
        ('pass', 'Passé'),
        ('fail', 'Échoué'),
        ('blocked', 'Bloqué'),
    ], string="Résultat global", tracking=True)

    step_ids = fields.One2many('test.run.step', 'test_run_id', string="Étapes exécutées")

    # Champs Jenkins (alimentés par Jenkins via RPC)
    jenkins_build_number = fields.Integer(string="Numéro de build", readonly=True)
    jenkins_build_url = fields.Char(string="URL du build", readonly=True)
    jenkins_build_status = fields.Selection([
        ('pending', 'En attente'),
        ('running', 'En cours'),
        ('success', 'Succès'),
        ('failed', 'Échoué'),
        ('aborted', 'Annulé'),
    ], string="Statut Jenkins", readonly=True)
    jenkins_log = fields.Text(string="Logs Jenkins", readonly=True)

    # Champs exécution manuelle
   # notes = fields.Text(string="Notes du testeur")
    environment = fields.Char(string="Environnement")
    browser = fields.Char(string="Navigateur / Plateforme")

    # -------------------------------------------------------------------------

    def action_start(self):
        self.ensure_one()
        if not self.test_case_id:
            raise UserError(_("Aucun Cas de test n'est associé à ce run."))

        if self.test_case_id.execution_mode == 'auto':
            if self.test_case_id.jenkins_job_status != 'created':
                self.test_case_id.action_launch_jenkins()
            self.test_case_id.action_run_jenkins(run_id=self.id)
            self.message_post(body="🤖 Exécution automatique lancée sur Jenkins.")
        else:
            self.message_post(body="▶️ Exécution manuelle démarrée.")

        self.write({'state': 'running'})
        return True

    def action_done(self):
        for record in self:
            record.write({'state': 'done'})
            if record.test_case_id:
                record.test_case_id.write({'state': 'done'})
        return True

    def action_compute_result(self):
        for run in self:
            states = run.step_ids.mapped('state')
            if not states:
                run.result = False
            elif 'fail' in states:
                run.result = 'fail'
            elif 'blocked' in states:
                run.result = 'blocked'
            else:
                run.result = 'pass'
        return True

    def action_auto_resolve_bugs(self, step_description=None):
        self.ensure_one()
        domain = [
            ('project_id', '=', self.project_id.id),
            ('state', 'not in', ['resolved', 'closed']),
        ]
        if step_description:
            domain.append(('description', 'ilike', step_description))
        bugs = self.env['test.bug'].search(domain)
        if bugs:
            bugs.write({'state': 'resolved'})
            for bug in bugs:
                bug.message_post(body="✅ Résolution automatique via Jenkins.")
        return True