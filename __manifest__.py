
{
    'name': 'Test Management',
    'version': '19.0.1.0',
    'category': 'Project',
    'depends': ['base', 'project', 'mail'],
    'data': ['security/category.xml','security/security.xml','security/ir.model.access.csv','views/test_case_views.xml', 'views/test_run_views.xml','views/test_bug_views.xml', 'views/menus.xml',],
    'installable': True,
    'application': True,
}
