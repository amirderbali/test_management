from odoo import models, fields, api

class TestDashboard(models.Model):
    _name = 'test.dashboard'
    _description = 'Dashboard QA'
    _auto = False  # Modèle virtuel

    @api.model
    def get_dashboard_data(self, project_id=None, task_id=None):
        """Retourne toutes les statistiques pour le dashboard avec filtres."""
        
        # ── 1. Construction des Domaines ORM ──────────────────────────────────
        case_dom = []
        run_dom = []
        bug_dom = []
        
        # SQL conditions pour les requêtes natives restantes (runs_by_day)
        sql_where_runs = "WHERE 1=1"
        
        if project_id:
            case_dom.append(('project_id', '=', int(project_id)))
            run_dom.append(('project_id', '=', int(project_id)))
            bug_dom.append(('project_id', '=', int(project_id)))
            sql_where_runs += f" AND project_id = {int(project_id)}"
            
        if task_id:
            case_dom.append(('task_id', '=', int(task_id)))
            run_dom.append(('task_id', '=', int(task_id)))
            bug_dom.append(('task_id', '=', int(task_id)))
            sql_where_runs += f" AND task_id = {int(task_id)}"

        # ── 2. Récupération des Données (ORM) ─────────────────────────────────
        TestCase = self.env['test.case']
        total_cases     = TestCase.search_count(case_dom)
        cases_draft     = TestCase.search_count(case_dom + [('state', '=', 'draft')])
        cases_approved  = TestCase.search_count(case_dom + [('state', '=', 'approved')])
        cases_progress  = TestCase.search_count(case_dom + [('state', '=', 'in_progress')])
        cases_done      = TestCase.search_count(case_dom + [('state', '=', 'done')])

        TestRun = self.env['test.run']
        total_runs   = TestRun.search_count(run_dom)
        runs_pass    = TestRun.search_count(run_dom + [('result', '=', 'pass')])
        runs_fail    = TestRun.search_count(run_dom + [('result', '=', 'fail')])
        runs_blocked = TestRun.search_count(run_dom + [('result', '=', 'blocked')])
        runs_running = TestRun.search_count(run_dom + [('state', '=', 'running')])

        pass_rate = round((runs_pass / total_runs * 100), 1) if total_runs else 0

        TestBug = self.env['test.bug']
        total_bugs    = TestBug.search_count(bug_dom)
        bugs_new      = TestBug.search_count(bug_dom + [('state', '=', 'new')])
        bugs_progress = TestBug.search_count(bug_dom + [('state', '=', 'in_progress')])
        bugs_resolved = TestBug.search_count(bug_dom + [('state', '=', 'resolved')])
        bugs_high     = TestBug.search_count(bug_dom + [('severity', '=', 'high')])
        bugs_medium   = TestBug.search_count(bug_dom + [('severity', '=', 'medium')])
        bugs_low      = TestBug.search_count(bug_dom + [('severity', '=', 'low')])

        # ── 3. Top 5 Projets par nombre de bugs (Corrigé via ORM) ─────────────
        # Utiliser read_group permet d'éviter l'affichage de [object Object]
        bug_data = self.env['test.bug'].read_group(
            domain=bug_dom,
            fields=['project_id'],
            groupby=['project_id'],
            orderby='project_id_count DESC',
            limit=5
        )

        top_projects = []
        for data in bug_data:
            if data['project_id']:
                # Odoo renvoie un tuple (id, "Nom du projet") pour les champs Many2one regroupés
                project_name = data['project_id'][1]
                top_projects.append({
                    'name': project_name,
                    'count': data['project_id_count']
                })

        # ── 4. Requête SQL pour l'activité des 7 derniers jours ───────────────
        self.env.cr.execute(f"""
            SELECT DATE(date) as day, COUNT(*) as total,
                   SUM(CASE WHEN result = 'pass' THEN 1 ELSE 0 END) as passed
            FROM test_run
            {sql_where_runs} AND date >= NOW() - INTERVAL '7 days'
            GROUP BY day
            ORDER BY day
        """)
        runs_by_day = [{'day': str(row[0]), 'total': row[1], 'passed': row[2]} for row in self.env.cr.fetchall()]

        # Liste globale pour remplir tes sélecteurs d'en-tête JS
        projects = self.env['project.project'].search_read([], ['id', 'name'])
        task_domain = [('project_id', '=', int(project_id))] if project_id else []
        tasks = self.env['project.task'].search_read(task_domain, ['id', 'name'])

        return {
            'test_cases': {'total': total_cases, 'draft': cases_draft, 'approved': cases_approved, 'in_progress': cases_progress, 'done': cases_done},
            'test_runs': {'total': total_runs, 'pass': runs_pass, 'fail': runs_fail, 'blocked': runs_blocked, 'running': runs_running, 'pass_rate': pass_rate},
            'bugs': {'total': total_bugs, 'new': bugs_new, 'in_progress': bugs_progress, 'resolved': bugs_resolved, 'high': bugs_high, 'medium': bugs_medium, 'low': bugs_low},
            'top_projects': top_projects,
            'runs_by_day': runs_by_day,
            'projects': projects,
            'tasks': tasks,
        }