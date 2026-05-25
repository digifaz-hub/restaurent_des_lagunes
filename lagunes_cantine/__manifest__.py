# -*- coding: utf-8 -*-
{
    'name': 'Cantine',
    'version': '18.0.3.0.0',
    'category': 'DIGIFAZ',
    'summary': 'Gestion de cantine d\'entreprise pour Restaurant des Lagunes',
    'description': """
        Module de gestion de cantine d'entreprise
        ==========================================

        Nouvelles fonctionnalités v3.0 :
        * Menus hebdomadaires (Samedi-Vendredi)
        * Types de plats configurables (Entrée, Plat, Dessert)
        * Catégories de menus (Africain, Européen, Végétarien)
        * Ingrédients pour chaque plat avec intégration automatique au marché
        * Règles d'affichage personnalisées par entreprise
        * Modification groupée des statuts de commandes
        * Historique complet des commandes

        Fonctionnalités existantes :
        * Gestion des entreprises clientes (type Cantine)
        * Gestion des plats (produits)
        * Commandes quotidiennes sans facturation immédiate
        * Site web pour prise de commande en ligne
        * Options de plat
        * Authentification sécurisée
        * Inscription des employés via lien unique
        * Export Excel des commandes
        * Heure limite de commande configurable
        * Facturation mensuelle consolidée
    """,
    'author': 'Restaurant des Lagunes',
    'website': 'xxxxx',
    'depends': [
        'base',
        'mail',
        'product',
        'sale_management',
        'web',
        'website',
        'lagunes_market',
    ],
    'data': [
        # Sécurité
        'security/lagunes_security.xml',
        'security/lagunes_cantine_security.xml',
        'security/ir.model.access.csv',
        'security/lagunes_ir_model_access.xml',

        # Données — chargées AVANT les vues
        'data/plat_types_data.xml',
        'data/product_data.xml',
        'data/plat_option_data.xml',
        'data/facturation_sequence_data.xml',
        'data/mail_template_data.xml',
        'data/week_menu_cron_data.xml',

        # ── Vues backend ─────────────────────────────────────────────────
        'views/res_partner_views.xml',

        # Rapports — DOIVENT être chargés AVANT les vues qui les référencent
        # via %(xmlid)d (ex: bouton "Imprimer PDF" sur le menu hebdomadaire).
        'report/report_lagunes_devis.xml',
        'report/report_week_menu.xml',

        # Nouvelles vues v3.0
        'views/lagunes_plat_type_views.xml',
        'views/lagunes_menu_category_views.xml',
        'views/lagunes_plat_ingredient_views.xml',
        'views/lagunes_partner_plat_type_rule_views.xml',
        'views/lagunes_week_menu_views.xml',

        # Vues existantes (mises à jour)
        'views/lagunes_plat_views.xml',
        'views/lagunes_plat_option_views.xml',

        'views/lagunes_commande_views.xml',

        # Héritage bon de commande
        'views/lagunes_sale_order_inherit_views.xml',

        # Wizards v3.0
        'wizard/commande_bulk_state_change_views.xml',
        'wizard/stock_insufficient_warning_views.xml',

        # Vues dont les actions sont référencées par lagunes_menus.xml
        'report/report_facturation_detail.xml',
        'views/lagunes_facturation_periode_views.xml',
        'views/lagunes_employe_views.xml',
        'views/lagunes_export_wizard_views.xml',
        'views/lagunes_employe_export_wizard_views.xml',
        
        # Menus principaux (DOIT être après toutes les actions des vues précédentes)
        'views/lagunes_menus.xml',

        # Vues Dashboard (qui utilisent menu_lagunes_cantine_root)
        'views/lagunes_dashboard_views.xml',

        # ── Templates Web ─────────────────────────────────────────────────
        # IMPORTANT : lagunes_menus.xml doit être AVANT les templates web
        # car website_menu_web.xml référence le menu principal du site
        'views/lagunes_menu_web.xml',

        'views/website_templates.xml',
        'views/website_commande_templates.xml',
        'views/website_inscription_templates.xml',
        'views/website_orders_templates.xml',

        # AJOUTÉ : template du menu hebdomadaire (manquait dans l'original)
        'views/website_week_menu_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lagunes_cantine/static/src/css/lagunes.css',
            'lagunes_cantine/static/src/css/cantine_style.css',
            'lagunes_cantine/static/src/js/utils/validation.js',
            'lagunes_cantine/static/src/js/utils/http.js',
            'lagunes_cantine/static/src/js/week_menu.js',
        ],
        'web.assets_backend': [
            'lagunes_cantine/static/src/css/lagunes.css',
            'lagunes_cantine/static/src/js/lagunes_patch.js',
            'lagunes_cantine/static/src/xml/dashboard_templates.xml',
            'lagunes_cantine/static/src/js/dashboard.js',
        ],
    },
    'demo': [
        'demo/demo_partners.xml',
        'demo/demo_references.xml',
        'demo/demo_plats.xml',
        'demo/demo_employes.xml',
        'demo/demo_week_menus.xml',
        'demo/demo_commandes.xml',
        'demo/demo_init_credentials.py',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
