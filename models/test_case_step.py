from odoo import models, fields

class TestCaseStep(models.Model):
    _name = 'test.case.step'
    _description = 'Test Case Step'
    _order = 'sequence'

    test_case_id = fields.Many2one(
        'test.case',
        string="Cas de Test",
        ondelete='cascade',
        required=True
    )

    sequence = fields.Integer(string="Ordre", default=1)
    description = fields.Text(string="Action à exécuter", required=True)
    expected_result = fields.Text(string="Résultat Attendu")