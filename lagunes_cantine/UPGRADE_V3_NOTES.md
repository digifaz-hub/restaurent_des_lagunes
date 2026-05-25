# Lagunes Cantine - Version 3.0 - Refonte complète

## 🎯 Objectifs d'upgrade

Refonte complète du système de gestion de cantine en ligne pour :
- Améliorer la flexibilité des menus
- Intégrer automatiquement la cantine avec le marché
- Améliorer l'expérience utilisateur (UI/UX)
- Tracer les mouvements de stock en détail

---

## ✅ Nouvelles fonctionnalités implémentées

### 1. **Menus hebdomadaires** (Samedi-Vendredi)
- **Modèle** : `lagunes_week_menu`
- **Vue** : Triple tableau hebdomadaire (Jour × Type de plat × Menu)
- **Statuts** : Draft → Published → Closed
- Configuration : Global ou par entreprise
- Vues XML complètes (formulaire, liste, recherche)

### 2. **Types de plats configurables**
- **Modèle** : `lagunes_plat_type`
- Entrée, Plat de résistance, Dessert (extensible)
- Couleurs personnalisées
- Vues XML complètes

### 3. **Catégories de menus**
- **Modèle** : `lagunes_menu_category`
- Menu Africain, Européen, Végétarien, Santé (extensible)
- Restriction d'accès par entreprise
- Icônes FontAwesome
- Vues XML complètes

### 4. **Ingrédients et intégration marché**
- **Modèle** : `lagunes_plat_ingredient`
- Liaison automatique plat ↔ article marché
- Quantités configurables
- Déduction automatique du stock à la préparation
- Support des ingrédients quantifiables/non-quantifiables

### 5. **Règles d'affichage par entreprise**
- **Modèle** : `lagunes_partner_plat_type_rule`
- Types de plats obligatoires/proposés par entreprise
- Nombre de choix par type configurable
- Visibilité personnalisée

### 6. **Modification groupée des statuts**
- **Wizard** : `lagunes_commande_bulk_state_change`
- Changer le statut de plusieurs commandes à la fois
- Option pour appliquer à toutes les commandes d'une entreprise
- Ajout de notes automatiques

### 7. **Historique des commandes**
- Champ `state_history` dans les commandes
- Enregistrement des changements de statut
- Traçabilité complète

### 8. **Mouvements de stock marché**
- **Modèle** : `lagunes_market_stock_movement` (nouveau marché)
- Types : Achat, Déduction cantine, Perte, Ajustement
- Suivi des soldes avant/après
- Vues XML complètes

### 9. **Tableau double entrée frontend**
- **Template** : `website_week_menu_template.xml`
- Affichage : Jours (colonnes) × Types de plats (lignes)
- Contrôleur : `week_menu.py`
- Route : `/cantine/menu`

### 10. **Historique commandes client**
- Routes : `/cantine/commandes/list` et `/cantine/commandes/<id>`
- Affichage groupé par date
- Détails complets de chaque commande

---

## 📁 Fichiers créés

### Modèles (`models/`)
```
lagunes_plat_type.py              # Types de plats
lagunes_menu_category.py          # Catégories de menus
lagunes_week_menu.py              # Menus hebdomadaires
lagunes_plat_ingredient.py        # Ingrédients des plats
lagunes_partner_plat_type_rule.py # Règles d'affichage
```

### Vues (`views/`)
```
lagunes_plat_type_views.xml               # Vues plat_type
lagunes_menu_category_views.xml           # Vues catégorie
lagunes_week_menu_views.xml               # Vues week_menu
lagunes_plat_ingredient_views.xml         # Vues ingrédients
lagunes_partner_plat_type_rule_views.xml  # Vues règles
website_week_menu_template.xml            # Template frontend
```

### Wizards (`wizard/`)
```
commande_bulk_state_change.py             # Modèle wizard
commande_bulk_state_change_views.xml      # Vues wizard
```

### Contrôleurs (`controllers/`)
```
week_menu.py                      # Routes frontend nouveau menu
```

### Données (`data/`)
```
plat_types_data.xml               # Types standards (Entrée, Plat, Dessert)
```

### Marché (`lagunes_market/`)
```
lagunes_market_stock_movement.py
views/lagunes_market_stock_movement_views.xml
```

---

## 🔗 Modifications apportées

### Fichiers modifiés

#### `models/lagunes_plat.py`
- **Avant** : Plat simple lié à product
- **Après** : 
  - Ajout `plat_type_id` (types de plats)
  - Ajout `ingredient_ids` (one2many ingrédients)

#### `models/lagunes_commande.py`
- **Avant** : Commande avec statut simple
- **Après** :
  - Ajout `state_history` (HTML historique)
  - Méthode `action_bulk_state_change()` 
  - Méthode `_deduct_ingredients_from_market()`
  - Intégration automatique marché

#### `models/__init__.py`
- Imports des 5 nouveaux modèles

#### `wizard/__init__.py` (créé)
- Import du wizard bulk_state_change

#### `controllers/__init__.py`
- Import du contrôleur week_menu

#### `__manifest__.py`
- Version : 18.0.2.0.0 → 18.0.3.0.0
- Dépendance : lagunes_market
- Toutes les nouvelles vues listées

---

## 🚀 Installation

1. **Mettre à jour le module**
```bash
cd /odoo18
python odoo-bin --config=odoo.conf --update=lagunes_cantine
```

2. **Data chargées automatiquement**
- Types de plats (Entrée, Plat, Dessert)
- Catégories menus (Africain, Européen, Végétarien, Santé)

3. **Vérifier l'installation**
- Menu Backend : Cantine → Types de plats
- Menu Backend : Cantine → Catégories de menus
- Menu Backend : Cantine → Menus hebdomadaires
- Frontend : `/cantine/menu`

---

## 📊 Flux de travail

### Backend (Administrateur)
1. Créer types de plats (si besoin)
2. Créer catégories de menus
3. Configurer règles d'affichage par entreprise
4. Créer le menu hebdomadaire (samedi-vendredi)
5. Affecter plats aux jours/types/catégories
6. Publier le menu

### Frontend (Client - Employé)
1. Authentification (code entreprise + email)
2. Voir le menu hebdomadaire (tableau double entrée)
3. Choisir ses plats selon les types autorisés
4. Consulter l'historique des commandes
5. Voir le statut des commandes

### Marché (Stock)
1. Lors de "En préparation" : déduction auto ingrédients
2. Enregistrement des mouvements de stock
3. Vue d'historique des mouvements

---

## ⚙️ Configuration par entreprise

Dans la fiche de l'entreprise cliente :

1. **Onglet "Cantine"**
2. **Bouton "Règles d'affichage des types"**
3. Configurer pour chaque type de plat :
   - Proposé (visible / non visible)
   - Obligatoire (doit en choisir / optionnel)
   - Nombre de choix

Exemple :
- Entrée : Proposée, optionnelle, 1 choix
- Plat : Obligatoire, 1 choix
- Dessert : Proposée, optionnelle, 1 choix

---

## 🔄 Intégration Cantine ↔ Marché

**Flux automatique** :

1. Créer un plat "Riz sauce arachide"
2. Ajouter ingrédients :
   - Riz blanc : 150g
   - Sauce arachide : 100g
   - Oignon : 50g
3. Marquer "Quantifiable" pour riz et sauce (pas pour oignon)
4. Un employé commande le plat
5. À "En préparation" :
   - Stock riz : -150g
   - Stock sauce : -100g
   - Mouvement de stock enregistré

---

## 🎨 Futures améliorations suggérées

1. **Widget agenda** frontend pour choisir les jours
2. **Export PDF du menu** personnalisé par entreprise
3. **Notifications** changements menu
4. **Recommandations** basées sur historique
5. **Prix dynamiques** selon jour/catégorie
6. **Allergie/Régimes** personnalisés par employé
7. **Mobile app** version légère

---

## 📝 Notes techniques

- **ORM** : Odoo 18 standard
- **Frontend** : HTML/CSS/JS vanilla (compatible Bootstrap 5)
- **Stock** : Déduction automatique à la transition "draft → preparing"
- **Sérialisation** : JSON pour les choix complexes
- **Compatibilité** : v18.0.3.0.0+

---

## 🔐 Sécurité & Permissions

- Access rules créées pour chaque modèle
- Vérification d'accs par entreprise (session)
- Historique d'actions traçable
- Stock protégé (lecture seule pour clients)

---

## 📞 Support

Pour questions/bugs :
- Consulter documentation interne
- Tester d'abord en dev
- Vérifier intégrité des données après migration

---

**Version** : 18.0.3.0.0  
**Date** : 8 avril 2026  
**Auteur** : Restaurant des Lagunes Tech Team
