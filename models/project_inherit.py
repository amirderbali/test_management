from odoo import models, fields, api
from odoo.exceptions import UserError

class ProjectProjectInherit(models.Model):
    _inherit = 'project.project'

    def action_delete_project(self):
        for project in self:
            # Vérifier si le projet a des tâches actives
            tasks = self.env['project.task'].search([
                ('project_id', '=', project.id)
            ])
            if tasks:
                raise UserError(
                    f"❌ Impossible de supprimer '{project.name}' "
                    f"— il contient {len(tasks)} tâche(s) !"
                )
            project.unlink()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'list',
            'target': 'current',
        }

# --- AJOUT POUR LA NAVIGATION VERS TEST MANAGEMENT ---

class ProjectTaskInherit(models.Model):
    _inherit = 'project.task'

    def action_open_test_management(self):
        """ Redirige vers la liste des Test Cases """
        return {
            'name': 'Test Cases',
            'type': 'ir.actions.act_window',
            'res_model': 'test.case',
            'view_mode': 'list,form',
            'target': 'current',
        }