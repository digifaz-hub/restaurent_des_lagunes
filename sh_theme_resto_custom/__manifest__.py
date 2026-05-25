# -*- coding: utf-8 -*-
{
    'name': 'SH Theme Restaurent des lagunes Custom',
    'version': '1.0.0',
    'category': 'Theme/Backend',
    'summary': 'Personnalisation des couleurs Odoo pour le Restaurent des lagunes',
    'description': """
Thème Personnalisé Restaurent des lagunes
===================================

Ce module personnalise les couleurs de l'interface Odoo Enterprise pour correspondre à la charte graphique de Restaurent des lagunes.

Couleurs principales:
- Bleu principal: #16166d
- Vert action: #7f910c

Ce module hérite de web_enterprise sans le modifier directement.
    """,
    'author': 'Restaurent des lagunes',
    'depends': ['web_enterprise'],
    'data': [],
    'assets': {
        'web._assets_primary_variables': [
            ('replace', 'web_enterprise/static/src/scss/primary_variables.scss',
             'sh_theme_resto_custom/static/src/scss/primary_variables.scss'),
        ],
        'web._assets_backend_helpers': [
            ('replace', 'web_enterprise/static/src/scss/bootstrap_overridden.scss',
             'sh_theme_resto_custom/static/src/scss/bootstrap_overridden.scss'),
            # Ajouter l'image de fond en light mode
            ('prepend', 'sh_theme_resto_custom/static/img/background-light.svg'),
        ],
        # ========= Dark Mode =========
        "web.dark_mode_variables": [
            ('replace', 'web_enterprise/static/src/scss/primary_variables_dark.scss',
             'sh_theme_resto_custom/static/src/scss/primary_variables_dark.scss'),
        ],
        "web.assets_web_dark": [
            ('replace', 'web_enterprise/static/src/scss/bootstrap_overridden_dark.scss',
             'sh_theme_resto_custom/static/src/scss/bootstrap_overridden_dark.scss'),
            ('replace', 'web_enterprise/static/src/scss/bs_functions_overridden_dark.scss',
             'sh_theme_resto_custom/static/src/scss/bs_functions_overridden_dark.scss'),
        ],
        'web.assets_backend_lazy_dark': [
            ('replace', 'web_enterprise/static/src/scss/bootstrap_overridden_dark.scss',
             'sh_theme_resto_custom/static/src/scss/bootstrap_overridden_dark.scss'),
            ('replace', 'web_enterprise/static/src/scss/bs_functions_overridden_dark.scss',
             'sh_theme_resto_custom/static/src/scss/bs_functions_overridden_dark.scss'),
        ],
        'web._assets_secondary_variables': [
            ('replace', 'web_enterprise/static/src/scss/secondary_variables.scss',
             'sh_theme_resto_custom/static/src/scss/secondary_variables.scss'),
        ],
        'web.assets_backend': [
            # Ajouter tes images SVG
            ('append', 'sh_theme_resto_custom/static/img/automation.svg'),
            ('append', 'sh_theme_resto_custom/static/img/background-light.svg'),
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
