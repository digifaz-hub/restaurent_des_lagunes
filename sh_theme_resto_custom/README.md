# SH Theme Resto Custom - Thème Personnalisé Restaurent des lagunes

## Description

Ce module personnalise les couleurs de l'interface Odoo Enterprise pour correspondre à la charte graphique de Restaurent des lagunes.

### Couleurs principales :
- **Bleu principal**: #16166d
- **Orange action**: #E65A2B

## Installation sur Odoo.sh

### Via Git (Recommandé)

1. Placez ce module dans votre repository Git dans le dossier `addons/`
2. Committez et pushez vers votre repository
3. Odoo.sh détectera automatiquement le module
4. Allez dans **Applications** → **Mettre à jour la liste des applications**
5. Recherchez "SH Theme Restaurent des lagunes Custom"
6. Cliquez sur **Installer**

### Via Backup ZIP

Si vous importez un backup, incluez ce module dans la structure :
```
backup_odoo_sh/
├── dump.sql
├── filestore/
└── addons/
    └── sh_theme_resto_custom/
```

## Structure du module

```
sh_theme_resto_custom/
├── __init__.py
├── __manifest__.py
├── README.md
└── static/
    ├── img/
    │   ├── automation.svg
    │   └── background-light.svg
    └── src/
        └── scss/
            ├── primary_variables.scss
            ├── primary_variables_dark.scss
            ├── bootstrap_overridden.scss
            ├── bootstrap_overridden_dark.scss
            ├── bs_functions_overridden_dark.scss
            ├── secondary_variables.scss
            └── secondary_variables_dark.scss
```

## Avantages de cette approche

✅ **Ne modifie pas web_enterprise** : Préserve l'intégrité du module Odoo officiel
✅ **Compatible avec les mises à jour** : Les mises à jour Odoo ne casseront pas votre thème
✅ **Facilement désactivable** : Désinstallez le module pour revenir aux couleurs par défaut
✅ **Support du mode sombre** : Inclut les personnalisations pour le dark mode
✅ **Maintenable** : Un seul module à gérer pour toutes vos personnalisations

## Désinstallation

Si vous souhaitez revenir aux couleurs par défaut :

1. Allez dans **Applications**
2. Recherchez "SH Theme Restaurent des lagunes Custom"
3. Cliquez sur **Désinstaller**
4. Videz le cache du navigateur

## Support

Pour toute question ou modification, contactez l'équipe technique de Restaurent des lagunes.

## Version

- **Version** : 1.0.0
- **Compatible avec** : Odoo 18 Enterprise
- **Dépendances** : web_enterprise
- **Licence** : LGPL-3
