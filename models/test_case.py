from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TestCase(models.Model):
    _name = 'test.case'
    _description = 'Test Case'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    # --- CHAMPS EXISTANTS ---
    name = fields.Char(string="Titre", required=True, tracking=True)
    description = fields.Text(string="Description")
    project_id = fields.Many2one('project.project', string="Projet", required=True)
    tache_id = fields.Many2one('project.task', string="Tache")
    user_id = fields.Many2one('res.users', string="Responsable")

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('approved', 'Approuvé'),
        ('in_progress', 'En cours'),
        ('done', 'Exécuté'),
    ], default='draft', tracking=True)

    step_ids = fields.One2many('test.case.step', 'test_case_id', string="Étapes de Test")

    # --- CHAMPS DE BASE ---
    reference = fields.Char(
        string="Référence", required=True, copy=False,
        readonly=True, index=True, default='Nouveau'
    )

    level = fields.Selection([
        ('unit', 'Unitaire'),
        ('integration', 'Intégration'),
        ('system', 'Système'),
        ('acceptance', 'Acceptation'),
    ], string="Niveau", default='system', tracking=True)

    test_type = fields.Selection([
        ('functional', 'Fonctionnel'),
        ('non_functional', 'Non Fonctionnel'),
        ('regression', 'Régression'),
        ('smoke', 'Smoke Test'),
        ('performance', 'Performance'),
        ('security', 'Sécurité'),
        ('usability', 'Utilisabilité'),
    ], string="Type de Test", default='functional', tracking=True)

    priority = fields.Selection([
        ('0', 'Normale'),
        ('1', 'Basse'),
        ('2', 'Haute'),
        ('3', 'Très Haute'),
    ], string="Priorité", default='0', tracking=True)

    sequence = fields.Integer(string="Séquence", default=10)
    duration_estimated = fields.Float(
        string="Durée estimée (min)",
        help="Temps estimé pour exécuter ce cas de test"
    )

    run_ids = fields.One2many('test.run', 'test_case_id', string="Exécutions")

    # --- NOUVEAUX CHAMPS : TRAÇABILITÉ ---

    user_story_ids = fields.Many2many(
        'project.task',
        'test_case_user_story_rel',
        'test_case_id',
        'task_id',
        string="User Stories",
        domain="[('project_id', '=', project_id)]",
        help="User stories couvertes par ce cas de test"
    )
    execution_mode = fields.Selection([
        ('manual', 'Manuel'),
        ('auto', 'Automatique'),
    ], string="Mode d'exécution", default='manual', tracking=True)

    sprint_id = fields.Many2one(
        'project.task.type',
        string="Sprint / Version",
        help="Sprint ou version auquel appartient ce cas de test",
        tracking=True
    )
   

    environment = fields.Selection([
        ('dev', 'Développement'),
        ('staging', 'Staging / Recette'),
        ('prod', 'Production'),
        ('all', 'Tous'),
    ], string="Environnement", default='staging', tracking=True)

    preconditions = fields.Text(
        string="Préconditions",
        help="État du système et données nécessaires avant d'exécuter le test"
    )

    test_data = fields.Text(
        string="Données de test",
        help="Jeux de données à utiliser lors de l'exécution"
    )

    expected_result_global = fields.Text(
        string="Résultat attendu global",
        help="Critère de succès global du cas de test"
    )

    obtained_result = fields.Text(
        string="Résultat obtenu",
        help="Résultat constaté lors de la dernière exécution"
    )

    reviewer_id = fields.Many2one(
        'res.users',
        string="Réviseur",
        help="Personne chargée de valider ce cas de test",
        tracking=True
    )

    due_date = fields.Date(string="Date d'échéance", tracking=True)

    # --- CHAMPS CALCULÉS ---
    step_count = fields.Integer(
        string="Nombre d'étapes",
        compute='_compute_step_count', store=True
    )
    run_count = fields.Integer(
        string="Nombre d'exécutions",
        compute='_compute_run_count'
    )
    bug_count = fields.Integer(
        string="Nombre de bugs",
        compute='_compute_bug_count'
    )
    user_story_count = fields.Integer(
        string="Nombre de User Stories",
        compute='_compute_user_story_count'
    )

    last_run_status = fields.Selection([
        ('never', 'Jamais exécuté'),
        ('passed', 'Succès'),
        ('failed', 'Échec'),
        ('blocked', 'Bloqué'),
    ], string="Dernier statut", compute='_compute_last_run_status', store=True)

    # --- MÉTHODES DE CALCUL ---

    @api.depends('reference', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.reference and record.reference != 'Nouveau':
                record.display_name = f"[{record.reference}] {record.name}"
            else:
                record.display_name = record.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'Nouveau') == 'Nouveau':
                vals['reference'] = self.env['ir.sequence'].next_by_code('test.case') or 'Nouveau'
        return super().create(vals_list)

    @api.depends('step_ids')
    def _compute_step_count(self):
        for rec in self:
            rec.step_count = len(rec.step_ids)

    @api.depends('run_ids')
    def _compute_run_count(self):
        for rec in self:
            rec.run_count = len(rec.run_ids)

    def _compute_bug_count(self):
        for rec in self:
            try:
                rec.bug_count = self.env['bug'].search_count([('test_case_id', '=', rec.id)])
            except Exception:
                rec.bug_count = 0

    @api.depends('user_story_ids')
    def _compute_user_story_count(self):
        for rec in self:
            rec.user_story_count = len(rec.user_story_ids)

    @api.depends('run_ids.state')
    def _compute_last_run_status(self):
        for rec in self:
            completed_runs = rec.run_ids.filtered(
                lambda r: r.state in ['passed', 'failed', 'blocked']
            )
            if completed_runs:
                latest_run = completed_runs.sorted('create_date', reverse=True)[0]
                rec.last_run_status = latest_run.state
            else:
                rec.last_run_status = 'never'

    # --- ACTIONS ---

    def action_approve(self):
        for rec in self:
            if rec.step_count == 0:
                raise ValidationError(_(
                    "Impossible d'approuver un cas de test vide. "
                    "Veuillez ajouter au moins une étape."
                ))
            rec.state = 'approved'

    def action_start(self):
        self.state = 'in_progress'
        step_vals = []
        for step in self.step_ids:
            step_vals.append((0, 0, {
                'sequence': step.sequence,
                'description': step.description,
                'expected_result': step.expected_result, }))
        
        
        
        
        
        
        
        new_run = self.env['test.run'].create({
            'name': f'Execution - {self.name}',
            'test_case_id': self.id,
            'project_id': self.project_id.id,
            'tache_id': self.tache_id.id if self.tache_id else False,
            'description': self.description,
            'expected_result': self.expected_result_global,
            
            'step_ids': step_vals,

            'state': 'draft',
        })
        new_run.action_start()

    def action_done(self):
        self.state = 'done'

    def action_reset(self):
        self.state = 'draft'

    # --- NAVIGATION BOUTONS ---

    def action_open_project(self):
        return {
            'name': 'Projet',
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'form',
            'res_id': self.project_id.id,
            'target': 'current',
        }

    def action_open_task(self):
        return {
            'name': 'Tâche',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': self.tache_id.id,
            'target': 'current',
        }

    def action_open_runs(self):
        return {
            'name': 'Exécutions',
            'type': 'ir.actions.act_window',
            'res_model': 'test.run',
            'view_mode': 'list,form',
            'domain': [('test_case_id', '=', self.id)],
            'context': {
                'default_test_case_id': self.id,
                'default_project_id': self.project_id.id,
            },
        }

    def action_open_bugs(self):
        return {
            'name': 'Bugs',
            'type': 'ir.actions.act_window',
            'res_model': 'bug',
            'view_mode': 'list,form',
            'domain': [('test_case_id', '=', self.id)],
            'context': {'default_test_case_id': self.id},
        }

    def action_open_user_stories(self):
        return {
            'name': 'User Stories',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.user_story_ids.ids)],
        }

    @api.model
    def get_dashboard_stats(self):
        total_cases = self.env['test.case'].search_count([])
        passed_runs = self.env['test.run'].search_count([('state', '=', 'passed')])
        failed_runs = self.env['test.run'].search_count([('state', '=', 'failed')])
        open_bugs = self.env['bug'].search_count([('state', '!=', 'done')])
        return {
            'total_cases': total_cases,
            'passed_runs': passed_runs,
            'failed_runs': failed_runs,
            'open_bugs': open_bugs,
        }


class ProjectTaskInherit(models.Model):
    _inherit = 'project.task'

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks:
            if task.project_id:
                self.env['test.case'].create({
                    'name': f' {task.name}',
                    'project_id': task.project_id.id,
                    'tache_id': task.id,
                    'state': 'draft',
                })
        return tasks