from odoo import models, fields, api, _

class TestBug(models.Model):
    _name = 'test.bug'
    _description = 'Test Bug'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc' # Affiche les nouveaux bugs en premier

    # --- CHAMPS EXISTANTS ---
    name = fields.Char(string="Titre du Bug", required=True, tracking=True)
    description = fields.Text(string="Description")
    
    severity = fields.Selection([ 
        ('low', 'Faible'),
        ('medium', 'Moyen'),
        ('high', 'Elevé')
    ], string="Sévérité", default='medium', tracking=True)

    state = fields.Selection([
        ('new', 'Nouveau'),
        ('confirmed', 'Confirmé'),
        ('in_progress', 'En cours'),
        ('resolved', 'Résolu'),
        ('closed', 'Fermé')
    ], string="Statut", default='new', tracking=True)

    test_run_id = fields.Many2one('test.run', string="Test Run", help="Le run à l'origine du bug")
    step_id = fields.Many2one('test.run.step', string="Step du Test")
    tester_id = fields.Many2one('res.users', string="Testeur (Rapporteur)", default=lambda self: self.env.user, tracking=True)
    project_id = fields.Many2one('project.project', string="Projet")

    # --- NOUVEAUX CHAMPS (Métadonnées et Résolution) ---
    reference = fields.Char(string="Référence", required=True, copy=False, readonly=True, index=True, default='Nouveau')
    
    test_case_id = fields.Many2one('test.case', related='test_run_id.test_case_id', store=True, string="Cas de Test")
    
    priority = fields.Selection([
        ('0', 'Basse'),
        ('1', 'Moyenne'),
        ('2', 'Haute'),
        ('3', 'Urgente'),
    ], string="Priorité", default='0', tracking=True)

    assignee_id = fields.Many2one('res.users', string="Assigné à (Développeur)", tracking=True)

    date_reported = fields.Datetime(string="Signalé le", default=fields.Datetime.now, readonly=True)
    date_resolved = fields.Datetime(string="Résolu le", readonly=True)
    date_closed = fields.Datetime(string="Fermé le", readonly=True)

    time_to_resolve = fields.Float(string="Temps de résolution (h)", compute='_compute_time_to_resolve', store=True)

    resolution_note = fields.Html(string="Note de résolution")

    # Dépendent du test.run (Assure-toi que environment et build_version existent dans test.run)
    #environment = fields.Char(string="Environnement", related='test_run_id.environment', store=True)
    #build_version = fields.Char(string="Version Build", related='test_run_id.build_version', store=True)

    # --- MÉCANIQUE DE RE-TEST AUTOMATIQUE ---
    retest_run_ids = fields.Many2many('test.run', compute='_compute_retest_runs', string="Runs de Re-test")
    retest_count = fields.Integer(string="Nombre de re-tests", compute='_compute_retest_runs')
    last_retest_status = fields.Selection([
        ('none', 'Aucun'),
        ('passed', 'Succès'),
        ('failed', 'Échec')
    ], string="Statut dernier re-test", compute='_compute_retest_runs')

    # --- MÉTHODES ET COMPUTED ---
    @api.depends('reference', 'name')
    def _compute_display_name(self):
        """ Format: [BUG-2026-00315] Login crash on Safari """
        for rec in self:
            if rec.reference and rec.reference != 'Nouveau':
                rec.display_name = f"[{rec.reference}] {rec.name}"
            else:
                rec.display_name = rec.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'Nouveau') == 'Nouveau':
                vals['reference'] = self.env['ir.sequence'].next_by_code('test.bug') or 'Nouveau'
        return super().create(vals_list)

    @api.depends('date_reported', 'date_resolved')
    def _compute_time_to_resolve(self):
        """ Calcule le délai de résolution en heures """
        for rec in self:
            if rec.date_reported and rec.date_resolved:
                delta = rec.date_resolved - rec.date_reported
                rec.time_to_resolve = delta.total_seconds() / 3600.0
            else:
                rec.time_to_resolve = 0.0

    @api.depends('test_case_id', 'date_resolved')
    def _compute_retest_runs(self):
        """ Cherche les exécutions du même cas de test effectuées APRÈS la date de résolution du bug """
        for rec in self:
            if rec.test_case_id and rec.date_resolved:
                runs = self.env['test.run'].search([
                    ('test_case_id', '=', rec.test_case_id.id),
                    ('create_date', '>', rec.date_resolved)
                ], order='create_date desc')
                
                rec.retest_run_ids = runs.ids
                rec.retest_count = len(runs)
                
                if runs:
                    latest_run = runs[0]
                    if latest_run.state == 'passed':
                        rec.last_retest_status = 'passed'
                    elif latest_run.state in ('failed', 'blocked'):
                        rec.last_retest_status = 'failed'
                    else:
                        rec.last_retest_status = 'none' # En cours ou brouillon
                else:
                    rec.last_retest_status = 'none'
            else:
                rec.retest_run_ids = False
                rec.retest_count = 0
                rec.last_retest_status = 'none'

    # --- ACTIONS (WORKFLOW) ---
    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'

    def action_resolve(self):
        for rec in self:
            rec.state = 'resolved'
            rec.date_resolved = fields.Datetime.now() # Horodatage de la résolution Dev

    def action_close(self):
        for rec in self:
            rec.state = 'closed'
            rec.date_closed = fields.Datetime.now() # Horodatage de l'acceptation QA

    def action_reset(self):
        for rec in self:
            rec.state = 'new'
            rec.date_resolved = False
            rec.date_closed = False

    def action_view_test_run(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Test Run Associé',
            'res_model': 'test.run',
            'view_mode': 'form',
            'res_id': self.test_run_id.id,
            'target': 'current',
        }