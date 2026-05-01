from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


def _build_jenkins_xml(vals):
    trigger_blocks = ""
    if vals.get('trigger_webhook'):
        trigger_blocks += (
            "\n        <com.cloudbees.jenkins.GitHubPushTrigger plugin=\"github\">"
            "\n          <spec></spec>"
            "\n        </com.cloudbees.jenkins.GitHubPushTrigger>"
        )
    if vals.get('trigger_poll') and vals.get('cron_expression'):
        trigger_blocks += (
            f"\n        <hudson.triggers.SCMTrigger>"
            f"\n          <spec>{vals['cron_expression']}</spec>"
            f"\n        </hudson.triggers.SCMTrigger>"
        )

    discard_block = ""
    if vals.get('discard_old_builds'):
        keep = vals.get('keep_builds_count', 10)
        discard_block = f"""
  <buildDiscarder>
    <strategy class="hudson.tasks.LogRotator">
      <numToKeepStr>{keep}</numToKeepStr>
    </strategy>
  </buildDiscarder>"""

    creds_block = ""
    if vals.get('git_credentials_id') and vals['git_credentials_id'] != 'none':
        creds_block = f"\n              <credentialsId>{vals['git_credentials_id']}</credentialsId>"

    env = vals.get('jenkins_env', '')
    branch = vals.get('jenkins_branch', '')
    repo_url = vals.get('git_repo_url', '')
    scm_branch = vals.get('git_scm_branch', '*/main')
    jenkinsfile_path = vals.get('jenkinsfile_path', 'Jenkinsfile')

    xml = f"""<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <description>Job généré depuis Odoo Test Management — ENV: {env} — BRANCH: {branch}</description>
  <keepDependencies>false</keepDependencies>
  <properties>
    <hudson.model.ParametersDefinitionProperty>
      <parameterDefinitions>
        <hudson.model.StringParameterDefinition>
          <name>ODOO_TEST_RUN_ID</name>
          <defaultValue></defaultValue>
          <description>ID du Test Run envoyé par Odoo</description>
          <trim>false</trim>
        </hudson.model.StringParameterDefinition>
      </parameterDefinitions>
    </hudson.model.ParametersDefinitionProperty>
    <org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
      <triggers>{trigger_blocks}
      </triggers>
    </org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>{discard_block}
  </properties>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition">
    <scm class="hudson.plugins.git.GitSCM">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>{repo_url}</url>{creds_block}
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches>
        <hudson.plugins.git.BranchSpec>
          <name>{scm_branch}</name>
        </hudson.plugins.git.BranchSpec>
      </branches>
      <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
      <submoduleCfg class="empty-list"/>
      <extensions/>
    </scm>
    <scriptPath>{jenkinsfile_path}</scriptPath>
    <lightweight>true</lightweight>
  </definition>
</flow-definition>"""
    return xml


class TestCaseJenkins(models.Model):
    _inherit = 'test.case'

    jenkins_job_name = fields.Char(string="Job Name (Jenkins)", tracking=True)
    jenkins_branch = fields.Char(string="Branche (BRANCH)", default="main", tracking=True)
    jenkins_env = fields.Selection([
        ('staging', 'Staging'),
        ('production', 'Production'),
        ('integration', 'Integration'),
    ], string="Environnement (ENV)", default='staging', tracking=True)

    git_repo_url = fields.Char(string="URL Repository GitHub", tracking=True)
    git_scm_branch = fields.Char(string="Branche SCM", default="*/main")
    git_credentials_id = fields.Char(string="Credentials Jenkins", default="github-token")
    jenkinsfile_path = fields.Char(string="Chemin Jenkinsfile", default="Jenkinsfile")

    trigger_webhook = fields.Boolean(string="Webhook GitHub (push)", default=True)
    trigger_poll = fields.Boolean(string="Poll SCM (cron)", default=False)
    cron_expression = fields.Char(string="Expression cron", default="H/15 * * * *")

    discard_old_builds = fields.Boolean(string="Supprimer les anciens builds", default=True)
    keep_builds_count = fields.Integer(string="Conserver N builds", default=10)

    jenkins_job_url = fields.Char(string="URL du Job Jenkins", readonly=True, tracking=True)
    jenkins_job_status = fields.Selection([
        ('not_created', 'Non créé'),
        ('created', 'Créé'),
        ('error', 'Erreur'),
    ], string="Statut Jenkins", default='not_created', readonly=True, tracking=True)
    jenkins_last_error = fields.Text(string="Dernière erreur Jenkins", readonly=True)
    jenkins_created_date = fields.Datetime(string="Créé le (Jenkins)", readonly=True)
    jenkins_xml_preview = fields.Text(string="XML Jenkins (aperçu)", compute='_compute_jenkins_xml')

    @api.depends(
        'jenkins_job_name', 'jenkins_branch', 'jenkins_env',
        'git_repo_url', 'git_scm_branch', 'git_credentials_id',
        'jenkinsfile_path', 'trigger_webhook', 'trigger_poll',
        'cron_expression', 'discard_old_builds', 'keep_builds_count',
    )
    def _compute_jenkins_xml(self):
        for rec in self:
            rec.jenkins_xml_preview = _build_jenkins_xml({
                'jenkins_env': rec.jenkins_env or '',
                'jenkins_branch': rec.jenkins_branch or '',
                'git_repo_url': rec.git_repo_url or '',
                'git_scm_branch': rec.git_scm_branch or '*/main',
                'git_credentials_id': rec.git_credentials_id or 'none',
                'jenkinsfile_path': rec.jenkinsfile_path or 'Jenkinsfile',
                'trigger_webhook': rec.trigger_webhook,
                'trigger_poll': rec.trigger_poll,
                'cron_expression': rec.cron_expression or '',
                'discard_old_builds': rec.discard_old_builds,
                'keep_builds_count': rec.keep_builds_count or 10,
            })

    @api.onchange('name')
    def _onchange_name_jenkins_job(self):
        if self.name and not self.jenkins_job_name:
            self.jenkins_job_name = self.name.replace(' ', '_')

    def action_launch_jenkins(self):
        """CRÉER le job Jenkins UNIQUEMENT — sans lancer le build."""
        self.ensure_one()

        if not self.jenkins_job_name:
            raise UserError(_("Le champ 'Job Name (Jenkins)' est obligatoire."))
        if not self.git_repo_url:
            raise UserError(_("L'URL du repository GitHub est obligatoire."))

        config = self.env['jenkins.config'].get_active_config()
        xml_body = _build_jenkins_xml({
            'jenkins_env': self.jenkins_env or '',
            'jenkins_branch': self.jenkins_branch or '',
            'git_repo_url': self.git_repo_url,
            'git_scm_branch': self.git_scm_branch or '*/main',
            'git_credentials_id': self.git_credentials_id or 'none',
            'jenkinsfile_path': self.jenkinsfile_path or 'Jenkinsfile',
            'trigger_webhook': self.trigger_webhook,
            'trigger_poll': self.trigger_poll,
            'cron_expression': self.cron_expression or '',
            'discard_old_builds': self.discard_old_builds,
            'keep_builds_count': self.keep_builds_count or 10,
        })

        base_url = config.jenkins_url.rstrip('/')
        create_url = f"{base_url}/createItem?name={self.jenkins_job_name}"
        auth = (config.jenkins_user, config.jenkins_token)

        try:
            resp = requests.post(
                create_url,
                data=xml_body.encode('utf-8'),
                auth=auth,
                headers={'Content-Type': 'application/xml; charset=utf-8'},
                timeout=30,
            )
        except Exception as e:
            self.write({'jenkins_job_status': 'error', 'jenkins_last_error': str(e)})
            raise UserError(_(f"Erreur Jenkins : {str(e)}"))

        job_url = f"{base_url}/job/{self.jenkins_job_name}"

        if resp.status_code in (200, 201):
            # ✅ On crée UNIQUEMENT — pas de build automatique ici
            self.write({
                'jenkins_job_status': 'created',
                'jenkins_job_url': job_url,
                'jenkins_last_error': False,
                'jenkins_created_date': fields.Datetime.now(),
            })
            self.message_post(body=_("✅ Job Jenkins créé — prêt à être lancé via 'Démarrer'."))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Job créé. Utilisez le bouton "Démarrer" sur le Test Run pour lancer les tests.'),
                    'type': 'success',
                    'sticky': True,
                }
            }
        elif resp.status_code == 400 and 'already exists' in resp.text.lower():
            raise UserError(_("Ce nom de job existe déjà sur Jenkins."))
        else:
            self.write({'jenkins_job_status': 'error', 'jenkins_last_error': resp.text})
            raise UserError(_(f"Erreur Jenkins {resp.status_code} : {resp.text}"))

    def action_run_jenkins(self, run_id):
        """
        LANCER le build Jenkins avec ODOO_TEST_RUN_ID.
        Appelé depuis test.run.action_start() avec l'ID du Test Run.
        """
        self.ensure_one()

        if self.jenkins_job_status != 'created':
            raise UserError(_(
                "Le job Jenkins n'existe pas encore. "
                "Créez-le d'abord via le bouton 'Créer Job Jenkins'."
            ))

        if not self.jenkins_job_name:
            raise UserError(_("Le nom du job Jenkins est manquant."))

        config = self.env['jenkins.config'].get_active_config()
        base_url = config.jenkins_url.rstrip('/')
        auth = (config.jenkins_user, config.jenkins_token)

        # ✅ /buildWithParameters obligatoire quand le job a des paramètres
        build_url = f"{base_url}/job/{self.jenkins_job_name}/buildWithParameters"

        try:
            resp = requests.post(
                build_url,
                params={'ODOO_TEST_RUN_ID': str(run_id)},
                auth=auth,
                timeout=15,
            )
            # Jenkins répond 201 Created quand il accepte le build
            if resp.status_code not in (200, 201):
                raise UserError(_(
                    f"Erreur Jenkins ({resp.status_code}) : {resp.text}"
                ))

            self.message_post(body=_(f"🚀 Build lancé (Test Run ID={run_id})"))
            _logger.info("Jenkins build triggered for job=%s run_id=%s", self.jenkins_job_name, run_id)

        except UserError:
            raise
        except Exception as e:
            raise UserError(_(f"Connexion Jenkins échouée : {str(e)}"))

    def action_open_jenkins_job(self):
        self.ensure_one()
        if not self.jenkins_job_url:
            raise UserError(_("Le job Jenkins n'a pas encore été créé."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.jenkins_job_url,
            'target': 'new',
        }

    def action_preview_jenkins_xml(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'XML Jenkins',
            'res_model': 'jenkins.xml.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_test_case_id': self.id,
                'default_xml_content': self.jenkins_xml_preview,
            },
        }