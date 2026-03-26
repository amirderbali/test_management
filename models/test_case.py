from odoo import models, fields

class TestCase(models.Model):
    _name = 'test.case'
    _description = 'Test Case'

    name = fields.Char(string="Titre", required=True, tracking =True)
    description = fields.Text(string="Description")
    _inherit = ['mail.thread', 'mail.activity.mixin']
    project_id = fields.Many2one(
        'project.project',
        string="Projet",
        required=True
    )
    tache_id = fields.Many2one('project.task', string="Tache")


    user_id = fields.Many2one(
        'res.users',
        string="Responsable"
    )
      
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('approved', 'Approuvé'),
        ('in_progress', 'En cours'),
        ('done', 'Exécuté'),
    ], default='draft', tracking=True)

    step_ids = fields.One2many(
        'test.case.step',
        'test_case_id',
        string="Étapes de Test"
    )

    # Boutons Workflow
    def action_approve(self):
        self.state = 'approved'

    def action_start(self):
        self.state = 'in_progress'

    def action_done(self):
        self.state = 'done'

    def action_reset(self):
        self.state = 'draft'