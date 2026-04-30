from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class JenkinsConfig(models.Model):
    """Configuration globale du serveur Jenkins (un seul enregistrement)."""
    _name = 'jenkins.config'
    _description = 'Configuration Jenkins'

    name = fields.Char(string="Nom", default="Jenkins Server", required=True)
    jenkins_url = fields.Char(
        string="URL Jenkins",
        required=True,
        help="Ex: http://localhost:8080",
    )
    jenkins_user = fields.Char(string="Utilisateur Jenkins", required=True)
    jenkins_token = fields.Char(
        string="Token API Jenkins",
        required=True,
        password=True,
        help="Générez-le depuis : Jenkins > Votre compte > Configure > API Token",
    )
    active = fields.Boolean(default=True)

    @api.model
    def get_active_config(self):
        config = self.search([], limit=1)
        if not config:
            raise UserError(_(
                "Aucune configuration Jenkins trouvée.\n"
                "Allez dans Paramètres > Configuration Jenkins pour en créer une."
            ))
        return config

    def test_connection(self):
        """Teste la connexion au serveur Jenkins."""
        self.ensure_one()
        try:
            resp = requests.get(
                f"{self.jenkins_url.rstrip('/')}/api/json",
                auth=(self.jenkins_user, self.jenkins_token),
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connexion réussie',
                        'message': f"Connecté à Jenkins : {data.get('nodeName', 'OK')}",
                        'type': 'success',
                    }
                }
            else:
                raise UserError(_(f"Erreur Jenkins HTTP {resp.status_code}: {resp.text[:200]}"))
        except requests.exceptions.ConnectionError:
            raise UserError(_(f"Impossible de joindre Jenkins à l'URL : {self.jenkins_url}"))
        except UserError:
            raise
        except Exception as e:
            raise UserError(_(f"Erreur inattendue : {str(e)}"))