# 🛒 lagunes_market — Hub Logistique & Stock Central
**Version** : 18.0.4.0.0 | **Cœur de l'écosystème Lagunes**

> Ce module est le **pilier logistique** de la solution. Il centralise l'approvisionnement en matières premières et fournit les services de gestion de stock en temps réel à tous les autres modules (`lagunes_cantine` et `lagunes_traiteur`).

---

## 1. Vue d'ensemble
`lagunes_market` gère le cycle complet des achats traditionnels (marché informel au comptant) :
- **Référentiel Article** : Catalogue indépendant des articles bruts (Tomates, Riz, Viandes, etc.).
- **Gestion de Stock** : Inventaire permanent par société avec calcul d'autonomie.
- **Dépenses** : Enregistrement des sorties de fonds et génération de pièces comptables.
- **Alertes** : Détection prédictive des ruptures et des hausses de prix.

---

## 2. Architecture des Modèles (ORM)

### 2.1 Cœur du Stock
*   **`lagunes.market.article`** : Fiche technique du produit brut.
    *   *Champs clés* : Catégorie, Unité par défaut, Prix moyen calculé.
*   **`lagunes.market.stock`** : État de l'inventaire par société.
    *   *Champ Clé* : `autonomy_days` (calculé sur la consommation moyenne des 30 derniers jours).
*   **`lagunes.market.stock.move`** : Grand livre immuable des mouvements. Chaque entrée/sortie est tracée avec une catégorie (`market`, `order_deduction`, `correction`).

### 2.2 Flux Opérationnel
*   **`lagunes.market`** : Document de "Marché" consolidant les achats du jour.
*   **`lagunes.market.line`** : Détail par article acheté (Quantité, Prix unitaire, Sous-total).
*   **`lagunes.market.leftover`** : Déclaration des reliquats du marché précédent pour réinitialisation du stock.

---

## 3. Fonctionnalités Avancées & KPIs

### 3.1 Dashboard Premium (OWL + Chart.js)
Le tableau de bord centralise 4 KPIs critiques :
1.  **Indice de Rotation** : Efficacité de renouvellement du stock.
2.  **Autonomie Moyenne** : Nombre de jours avant rupture totale théorique.
3.  **Dépenses Mensuelles** : Comparaison avec le mois précédent.
4.  **Points de Rupture** : Liste des articles sous le seuil critique.

### 3.2 Intelligence Analytique
*   **Calcul d'Autonomie** : Basé sur les mouvements `out` réels. Si un article n'est jamais consommé, l'autonomie est fixée à 999 jours.
*   **Surveillance des Prix** : Détecte les augmentations de prix > 5% entre deux marchés et alerte l'utilisateur par des badges visuels.

---

## 4. Intégration Inter-Modules (Centralisation)
Ce module expose des méthodes API internes utilisées par les autres modules :
- **Cantine** : Déduit automatiquement les ingrédients du stock `lagunes_market` lors de la validation des repas (si configuré).
- **Traiteur** : Utilise le stock `lagunes_market` pour vérifier la faisabilité des prestations et déduire les besoins lors de la production.

---

## 5. Sécurité et Multi-Société
- **Isolation** : Chaque site (Abidjan, Cocody, Bouaké) possède son propre stock indépendant via le champ `company_id`.
- **Héritage** : Les groupes `group_lagunes_manager` (Cantine) et `group_traiteur_commercial` (Traiteur) héritent automatiquement des droits de lecture de ce module.

---

## 6. Inventaire des Fichiers
| Fichier | Rôle |
|:---|:---|
| `models/lagunes_market.py` | Logique principale de validation et rollback (Stock + Compta). |
| `models/lagunes_market_stock.py` | Moteur de calcul des quantités (utilisant `SELECT FOR UPDATE` pour la concurrence). |
| `models/lagunes_market_dashboard.py` | Agrégation SQL pour les KPIs et graphiques du Dashboard. |
| `static/src/js/market_dashboard.js` | Composant OWL gérant l'affichage dynamique et les animations Chart.js. |
| `security/lagunes_market_security.xml` | Définition des Record Rules pour l'isolation multi-société. |

---
*Documentation générée pour Odoo 18 — Lagunes*