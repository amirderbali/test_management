
{
    'name': 'Test Management',
    'version': '19.0.1.0',
    'category': 'Project',
    'depends': ['base', 'project', 'mail'],
    'data': [
    'security/category.xml',
    'security/security.xml',
    'security/ir.model.access.csv',

    'views/test_case_views.xml',
    'views/test_run_views.xml',
    'views/test_bug_views.xml',
    'views/test_dashboard_action.xml',


    #'views/test_dashboard.xml',    #AJOUTER ICI AVANT menus.xml

    'views/menus.xml',

    'views/test_report_action.xml',
    'views/test_report_template.xml',
    'views/inherit_views.xml',
    'views/jenkins_config_views.xml',
    'views/test_case_jenkins_views.xml',
],
    'assets': {
        'web.assets_backend': [
            
            'test_management/static/src/js/dashboard.js',
            'test_management/static/src/xml/dashboard.xml',
        ],
    },

    
    'installable': True,
    'application': True,
}
