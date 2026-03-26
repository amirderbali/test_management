from odoo import models,fields

class TestBug (models.Model):
    _name='test.bug'
    _description='Test Bug'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    description = fields.Text(string="Description")
    name = fields.Char(string="Titre du Bug", required=True)

    severity = fields.Selection([ ('low', 'Faible'),('medium', 'Moyen'),('high', 'Elevé')], string="Sévérité", default='medium', tracking=True)

    state = fields.Selection([('new', 'Nouveau'),('confirmed', 'Confirmé'),('in_progress', 'En cours'),('resolved', 'Résolu'),('closed', 'Fermé')
    ], string="Statut", default='new', tracking=True)

    test_run_id = fields.Many2one('test.run',string="Test Run" )

    step_id = fields.Many2one('test.run.step',string="Step du Test" )

    tester_id = fields.Many2one('res.users',string="Testeur",default=lambda self: self.env.user )

    project_id = fields.Many2one('project.project',string="Projet" )
    
    def action_confirm(self):
     for rec in self:
        rec.state = 'confirmed'
    def action_start(self):
     for rec in self:
        rec.state = 'in_progress'

    def action_resolve(self):
     for rec in self:
        rec.state = 'resolved'

    def action_close(self):
     for rec in self:
        rec.state = 'closed'

    def action_reset(self):
     for rec in self:
        rec.state = 'new'
    
    