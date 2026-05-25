# -*- coding: utf-8 -*-
{
    'name': 'Gestion des marchés',
    'version': '18.0.4.0.0',
    'summary': 'Gestion des marchés hebdomadaires d\'approvisionnement du restaurant',
    'description': """
        Module de gestion des marchés d'approvisionnement.

        v4.0.0 — Améliorations :
        - Unités de mesure en liste déroulante (lagunes.market.uom)
          → Remplacement du champ texte libre par un Many2one configurable
          → 10 unités préconfigurées : kg, g, litre, cl, pièce, botte, sachet, boîte, sac, tas
          → Gérables depuis Configuration → Unités de mesure
        - Correction : bouton Valider disparaît correctement après validation
        - Correction : "Pré-remplir depuis le stock actuel" recharge le formulaire
          pour afficher immédiatement le stock initial créé
        - Correction : sélection d'un article en ligne pré-remplit automatiquement
          la catégorie (readonly calculé) et l'unité de mesure (liste déroulante)
    """,
    'author': 'Lagunes',
    'category': 'DIGIFAZ',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'account', 'web'],
    'data': [
        # Sécurité
        'security/lagunes_market_security.xml',
        'security/ir.model.access.csv',
        # Données initiales
        'data/lagunes_market_data.xml',
        'data/lagunes_market_uom_data.xml',
        # Vues
        'views/lagunes_market_uom_views.xml',
        'views/lagunes_market_article_views.xml',
        'views/lagunes_market_views.xml',
        'views/lagunes_market_stock_views.xml',
        'views/lagunes_market_stock_alerts_views.xml',
        'wizard/lagunes_market_adjustment_wizard_views.xml',
        'views/lagunes_market_leftover_views.xml',
        'views/lagunes_market_config_views.xml',
        'views/lagunes_market_report_views.xml',
        'views/lagunes_market_dashboard_views.xml',
        # Rapport PDF
        'report/lagunes_market_report.xml',
        'report/lagunes_market_report_template.xml',
        # Menus (en dernier pour que les actions soient déjà définies)
        'views/lagunes_market_menu.xml',
    ],
    'demo': [
        'demo/demo_articles.xml',
        'demo/demo_stocks.xml',
        'demo/demo_markets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'lagunes_market/static/src/css/lagunes_market.css',
            'lagunes_market/static/src/js/market_dashboard.js',
            'lagunes_market/static/src/js/price_history_chart.js',
            'lagunes_market/static/src/xml/market_dashboard_templates.xml',
            'lagunes_market/static/src/xml/price_history_chart_templates.xml',
        ],

        'web.report_assets_common': [
            'lagunes_market/static/src/css/lagunes_market_report.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}