from odoo import models, fields, api

class TestCase(models.Model):
    _name = 'test.case'
    _description = 'Test Case'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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

    def action_approve(self):
        self.state = 'approved'

    def action_start(self):
        self.state = 'in_progress'
        new_run = self.env['test.run'].create({
            'name': f'Execution - {self.name}',
            'test_case_id': self.id,
            'project_id': self.project_id.id,
            'tache_id': self.tache_id.id if self.tache_id else False,
            'state': 'draft',
        })
        new_run.action_start()

    def action_done(self):
        self.state = 'done'

    def action_reset(self):
        self.state = 'draft'

    # ✅ NOUVEAU - Bouton vers le Projet
    def action_open_project(self):
        return {
            'name': 'Projet',
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'form',
            'res_id': self.project_id.id,
            'target': 'current',
        }

    # ✅ NOUVEAU - Bouton vers la Tâche
    def action_open_task(self):
        return {
            'name': 'Tâche',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': self.tache_id.id,
            'target': 'current',
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