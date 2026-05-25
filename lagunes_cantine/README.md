# 🍽️ Restaurant des Lagunes — Module Cantine

**Version** : 18.0.2.0.0  
**Licence** : LGPL-3  
**Catégorie** : Ventes  
**Dépendances** : `base`, `product`, `sale_management`, `website`

---

## 📋 Description

Module de gestion de cantine d'entreprise pour Odoo 18. Il permet au **Restaurant des Lagunes** de gérer les commandes quotidiennes de repas pour ses entreprises clientes, avec un portail web dédié pour les employés.

---

## ✨ Fonctionnalités principales

### 🏢 Gestion des entreprises clientes
- Enregistrement des entreprises clientes (`res.partner`)
- Code d'accès unique par entreprise pour la connexion des employés
- Lien d'inscription unique par entreprise (token sécurisé)
- Heure limite de commande configurable par entreprise
- Limite de commandes par jour calculée automatiquement (nombre d'employés actifs × commandes par session)

### 📅 Gestion des menus
- **Menus quotidiens** (`lagunes.menu`) : un menu actif par entreprise et par période
- **Menus hebdomadaires** (`lagunes.week.menu`) : menus complets avec entrée, plat de résistance et dessert
- Support de périodes multi-jours (date début → date fin)
- Contrainte d'unicité : un seul menu actif par entreprise et par période
- Vues : Kanban, Calendrier, Liste, Formulaire, Pivot, Graphique

### 🍲 Gestion des plats
- **Plats** (`lagunes.plat`) : liés à des produits Odoo pour la facturation
- **Options de plat** (`lagunes.plat.option`) : personnalisations (sans sel, piment à part, sauce à côté...)
- Options globales applicables à tous les plats
- Création automatique du produit associé si non fourni
- Images, catégories et prix unitaires

### 📝 Commandes
- **Commandes** (`lagunes.commande`) avec workflow complet :
  - `brouillon` → `confirmée` → `en_preparation` → `prete` → `livree`
  - Possibilité d'annulation à chaque étape
- Référence auto-générée (séquence)
- Contrôle de la limite de commandes par jour par entreprise
- Contrôle de l'heure limite de commande
- Options et notes personnalisées par commande
- Création de commande de vente (bon de commande Odoo) individuelle

### 💰 Facturation mensuelle
- **Périodes de facturation** (`lagunes.facturation.periode`) pour regrouper les commandes
- Workflow : `brouillon` → `confirmée` → `facturée` (ou `annulée`)
- Chargement automatique des commandes livrées non facturées
- Génération de devis/bons de commande consolidés
- Contrôle des chevauchements de périodes
- Duplication de période pour le mois suivant

### 👥 Gestion des employés
- **Employés** (`lagunes.employe`) : inscrits par entreprise
- Inscription via lien unique sécurisé (token par entreprise)
- Authentification par email + mot de passe
- Activation / Désactivation par le manager
- Contrainte d'unicité email par entreprise

### 📊 Exports et rapports
- **Export Excel** des commandes par période et par entreprise
- **Export PDF** professionnel via ReportLab
- **Rapport devis** personnalisé (QWeb)
- Statistiques commandes et menus (vues Pivot et Graphique)

### 🌐 Portail Web (Frontend)
- Page d'accueil de la cantine
- **Connexion employés** : code entreprise + email + mot de passe
- **Affichage du menu du jour** avec les plats disponibles
- **Commande en ligne** avec choix des options et notes
- **Historique** : consultation des commandes passées
- **Inscription** : formulaire d'inscription employé via lien unique
- **Confirmation de commande** avec page de récapitulatif

---

## 🏗️ Architecture technique

### Modèles de données

| Modèle | Description | Type |
|--------|-------------|------|
| `res.partner` | Entreprise cliente (héritage) | Héritage |
| `lagunes.menu` | Menu quotidien | Modèle |
| `lagunes.week.menu` | Menu hebdomadaire | Modèle |
| `lagunes.plat` | Plat (lié à `product.product`) | Modèle |
| `lagunes.plat.option` | Option de personnalisation | Modèle |
| `lagunes.commande` | Commande d'un employé | Modèle |
| `lagunes.employe` | Employé inscrit | Modèle |
| `lagunes.facturation.periode` | Période de facturation mensuelle | Modèle |
| `lagunes.export.wizard` | Assistant d'export commandes | Wizard |

### Contrôleurs (routes web)

| Route | Méthode | Description |
|-------|---------|-------------|
| `/cantine` | GET | Redirection vers la page d'accueil |
| `/cantine/home` | GET | Page d'accueil / connexion |
| `/cantine/verify` | POST | Vérification code entreprise + email |
| `/cantine/menu/<id>` | GET | Menu du jour pour l'entreprise |
| `/cantine/commander` | POST | Passer une commande |
| `/cantine/confirmation/<id>` | GET | Page de confirmation |
| `/cantine/mes-commandes` | GET | Historique des commandes |
| `/cantine/logout` | GET | Déconnexion |
| `/cantine/inscription/<token>` | GET | Formulaire d'inscription |
| `/cantine/inscription/<token>/submit` | POST | Soumission inscription |

### Fichiers statiques

| Fichier | Description |
|---------|-------------|
| `static/src/css/lagunes_frontend.css` | Styles du portail web |
| `static/src/css/lagunes_backend.css` | Styles du backend Odoo |
| `static/src/js/lagunes_commande.js` | JavaScript pour les commandes en ligne |
| `static/src/js/lagunes_patch.js` | Patch JS pour le backend |

---

## 🔐 Sécurité et droits d'accès

### Groupes de sécurité

| Groupe | Hérite de | Description |
|--------|-----------|-------------|
| **Utilisateur** | Utilisateur interne | Accès en lecture aux menus et commandes |
| **Cuisine** | Utilisateur | Lecture + écriture des commandes (préparation) |
| **Manager** | Cuisine | Accès complet à toutes les fonctionnalités |

### Droits par rôle

| Modèle | Utilisateur | Cuisine | Manager | Public |
|--------|:-----------:|:-------:|:-------:|:------:|
| Menu | 👁️ | 👁️ | ✅ CRUD | 👁️ |
| Menu Hebdo | 👁️ | 👁️ | ✅ CRUD | 👁️ |
| Plat | 👁️ | 👁️ | ✅ CRUD | 👁️ |
| Options plat | 👁️ | 👁️ | ✅ CRUD | — |
| Commande | 👁️ | 👁️ ✏️ | ✅ CRUD | ✏️ Créer |
| Facturation | 👁️ | 👁️ | ✅ CRUD | — |
| Employé | 👁️ | 👁️ | ✅ CRUD | ✏️ Créer |
| Export wizard | — | — | ✅ CRUD | — |

> **Légende** : 👁️ = Lecture seule, ✏️ = Écriture, ✅ CRUD = Lire/Créer/Modifier/Supprimer

### Règles d'enregistrement (Record Rules)

- **Utilisateur** : ne voit que les données de son entreprise
- **Cuisine** : lecture/écriture des commandes (toutes entreprises)
- **Manager** : accès total sans restriction

---

## 📁 Structure des fichiers

```
lagunes_cantine/
├── __init__.py
├── __manifest__.py
├── README.md
│
├── controllers/
│   └── main.py                          # Contrôleurs web (routes /cantine/*)
│
├── data/
│   ├── facturation_sequence_data.xml    # Séquences de facturation
│   ├── plat_option_data.xml             # Données initiales options
│   └── product_data.xml                 # Produits par défaut
│
├── models/
│   ├── __init__.py
│   ├── res_partner.py                   # Extension entreprise cliente
│   ├── lagunes_menu.py                  # Menus quotidiens
│   ├── lagunes_week_menu.py             # Menus hebdomadaires
│   ├── lagunes_plat.py                  # Plats
│   ├── lagunes_plat_option.py           # Options de plats
│   ├── lagunes_commande.py              # Commandes
│   ├── lagunes_employe.py               # Employés
│   ├── lagunes_facturation_periode.py   # Facturation mensuelle
│   ├── lagunes_export_wizard.py         # Wizard export Excel/PDF
│   ├── product_template.py             # Extension produit
│   ├── sale_order.py                    # Extension bon de commande
│   └── sale_order_line.py               # Extension ligne de commande
│
├── report/
│   └── report_lagunes_devis.xml         # Rapport devis personnalisé
│
├── security/
│   ├── lagunes_security.xml             # Groupes et règles d'accès
│   ├── lagunes_ir_model_access.xml      # Accès supplémentaires
│   └── ir.model.access.csv             # Matrice d'accès par modèle
│
├── static/
│   ├── description/
│   │   └── icon.png                     # Icône du module
│   └── src/
│       ├── css/
│       │   ├── lagunes_frontend.css     # Styles portail web
│       │   └── lagunes_backend.css      # Styles backend
│       └── js/
│           ├── lagunes_commande.js      # JS commandes en ligne
│           └── lagunes_patch.js         # Patch JS backend
│
└── views/
    ├── res_partner_views.xml            # Vues entreprise cliente
    ├── lagunes_menu_views.xml           # Vues menus (kanban, calendar, etc.)
    ├── lagunes_week_menu_views.xml      # Vues menus hebdomadaires
    ├── lagunes_plat_views.xml           # Vues plats
    ├── lagunes_plat_option_views.xml    # Vues options de plats
    ├── lagunes_commande_views.xml       # Vues commandes
    ├── lagunes_employe_views.xml        # Vues employés
    ├── lagunes_facturation_periode_views.xml # Vues facturation
    ├── lagunes_export_wizard_views.xml  # Vues wizard export
    ├── lagunes_sale_order_inherit_views.xml # Héritage bon de commande
    ├── lagunes_menus.xml                # Menus principaux backend
    ├── lagunes_menu_web.xml             # Menu website
    ├── website_templates.xml            # Templates web (accueil, login)
    ├── website_menu_templates.xml       # Template menu du jour
    ├── website_commande_templates.xml   # Templates commande en ligne
    └── website_inscription_templates.xml # Template inscription
```

---

## 🚀 Installation

### Prérequis
- Odoo 18 (Community ou Enterprise)
- Modules Odoo installés : `base`, `product`, `sale_management`, `website`

### Étapes

1. Copier le dossier `lagunes_cantine` dans votre répertoire `custom_addons`
2. Mettre à jour la liste des modules : **Apps > Mettre à jour la liste des apps**
3. Rechercher "**Restaurant des Lagunes**" dans les Apps
4. Cliquer sur **Installer**

### Configuration post-installation

1. **Assigner les rôles** : Paramètres > Utilisateurs > choisir le rôle "Manager" dans la section "Restaurant des Lagunes"
2. **Créer une entreprise cliente** : Restaurant Lagunes > Gestion > Entreprises Clientes
3. **Configurer l'heure limite** de commande et le nombre max de commandes par session sur la fiche entreprise
4. **Créer des plats** : Restaurant Lagunes > Menus - Plats > Plats
5. **Créer un menu** : Restaurant Lagunes > Menus - Plats > Menus Cantine
6. **Communiquer le lien d'inscription** aux employés de l'entreprise

---

## 🔄 Flux de travail typique

```
1. Manager crée une entreprise cliente
   └─→ Code d'accès et lien d'inscription générés automatiquement

2. Les employés s'inscrivent via le lien unique
   └─→ Compte créé avec email + mot de passe

3. Manager crée le menu du jour
   └─→ Sélection des plats

4. Les employés se connectent au portail web
   └─→ Code entreprise + email + mot de passe

5. Les employés passent commande en ligne
   └─→ Choix du plat + options + notes

6. La cuisine voit les commandes du jour
   └─→ Préparation → Prêt → Livré

7. En fin de mois, le manager facture
   └─→ Période de facturation → Chargement des commandes → Génération du devis
```

---

## 📝 Notes techniques

- **Pas de TVA** : Les plats sont créés sans TVA (régime micro-entreprise)
- **Prix masqués** : Les prix ne sont pas affichés aux employés sur le portail web
- **Sessions** : L'authentification employé utilise les sessions Odoo (pas de comptes utilisateur Odoo)
- **Heure limite** : Configurable par entreprise, contrôlée côté serveur
- **Export** : Formats disponibles Excel (openpyxl) et PDF (ReportLab)
