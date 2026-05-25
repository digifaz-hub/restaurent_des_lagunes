# 🔒 Audit Technique — lagunes_cantine & lagunes_market (Odoo 18)

## Résumé exécutif

**24 correctifs appliqués** — **0 item restant**. L'audit est complet.

| Catégorie | Critiques | Importants | Mineurs | Total |
|-----------|:---------:|:----------:|:-------:|:-----:|
| Sécurité | 5 | 2 | 2 | **9** |
| Fonctionnel | 3 | 3 | — | **6** |
| Architecture | — | 3 | 3 | **6** |
| Tests & Outillage | — | — | 3 | **3** |

---

## 🔴 Phase 1 — Correctifs Critiques de Sécurité

### 1. Mot de passe exposé via ORM
**Fichier**: [lagunes_employe.py](file:///C:/odoo18/custom_addons/lagunes_cantine/models/lagunes_employe.py#L62-L67)
```diff
-string='Mot de passe', help='Mot de passe pour la connexion au site web'
+string='Mot de passe (hash)', groups='base.group_system'
```

### 2. Création publique d'employés
**Fichier**: [ir.model.access.csv](file:///C:/odoo18/custom_addons/lagunes_cantine/security/ir.model.access.csv#L15)
```diff
-base.group_public,0,0,1,0
+base.group_public,0,0,0,0
```

### 3. Contournement d'authentification mot de passe
**Fichier**: [res_partner.py](file:///C:/odoo18/custom_addons/lagunes_cantine/models/res_partner.py#L388-L396)
— Si un hash existe en base, la vérification est maintenant **obligatoire** même sans `mot_de_passe` fourni.

### 4. Rate limiting sur `/cantine/verify_access`
**Fichier**: [main.py](file:///C:/odoo18/custom_addons/lagunes_cantine/controllers/main.py#L32-L50)
— 5 tentatives max / 60s par IP, avec logging d'audit.

### 5. Record rules inopérantes
**Fichier**: [lagunes_security.xml](file:///C:/odoo18/custom_addons/lagunes_cantine/security/lagunes_security.xml#L36-L62)
```diff
-[('entreprise_id', 'in', [user.partner_id.commercial_partner_id.id])]
+[('company_id', '=', user.company_id.id)]
```

---

## 🟠 Phase 2 — Bugs Fonctionnels

### 6. `_remove_quantity` retour dict traité comme bool
**Fichier**: [lagunes_market.py](file:///C:/odoo18/custom_addons/lagunes_market/models/lagunes_market.py#L250-L270)
```diff
-is_capped = stock_model._remove_quantity(...)
+result = stock_model._remove_quantity(..., allow_capped=True)
+if result.get('is_capped'):
```

### 7. `action_cancel` manquait `allow_capped=True`
**Fichier**: [lagunes_market.py](file:///C:/odoo18/custom_addons/lagunes_market/models/lagunes_market.py#L250-L270)

### 8. `_unique_together` ignoré silencieusement
**Fichier**: [lagunes_week_menu.py](file:///C:/odoo18/custom_addons/lagunes_cantine/models/lagunes_week_menu.py#L188-L192)
```diff
-_unique_together = [('week_menu_id', 'day', 'plat_type_id')]
+_sql_constraints = [('unique_menu_day_type', 'unique(week_menu_id, day, plat_type_id)', ...)]
```

### 9. `action_mark_invoiced` — ordre de write dangereux
**Fichier**: [lagunes_facturation_periode.py](file:///C:/odoo18/custom_addons/lagunes_cantine/models/lagunes_facturation_periode.py#L400-L417)
— Commandes écrites **avant** le changement d'état de la période.

### 10. `@api.depends` incomplet sur `prix_total`
**Fichier**: [lagunes_commande.py](file:///C:/odoo18/custom_addons/lagunes_cantine/models/lagunes_commande.py#L282-L283)
— Ajout de `option_ids.prix_supplementaire`.

### 11. `prix_supplementaire` compute inutile (toujours 0.0)
**Fichier**: [lagunes_plat_option.py](file:///C:/odoo18/custom_addons/lagunes_cantine/models/lagunes_plat_option.py#L46-L49)
— Remplacé par `default=0.0` simple.

---

## 🟡 Phase 3 — Architecture & Code

### 12. Dashboard imports fragiles (in-method)
**Fichier**: [lagunes_dashboard.py](file:///C:/odoo18/custom_addons/lagunes_cantine/models/lagunes_dashboard.py#L1-L8)
— 5 imports in-method supprimés, `json` et `datetime` au top-level. Stock KPIs ajoutés à `get_dashboard_data`.

### 13. Route `/cantine/api/plats-du-jour` dupliquée
**Fichier**: [api.py](file:///C:/odoo18/custom_addons/lagunes_cantine/controllers/api.py#L12-L14)
— Version incomplète supprimée, version `week_menu.py` conservée.

### 14. Centralisation de `is_plat_resistance` (3× dupliqué)
**Fichier**: [lagunes_week_menu.py](file:///C:/odoo18/custom_addons/lagunes_cantine/models/lagunes_week_menu.py#L263-L276)
— `@staticmethod _is_plat_resistance()` unique, appelé par compute et onchange.

### 15. `move_category` manquait `'adjustment'`
**Fichier**: [lagunes_market_stock.py](file:///C:/odoo18/custom_addons/lagunes_market/models/lagunes_market_stock.py#L433-L443)
— Ajout de `('adjustment', 'Ajustement manuel')`.

### 16. `company_id` manquant sur `lagunes.plat.option`
**Fichier**: [lagunes_plat_option.py](file:///C:/odoo18/custom_addons/lagunes_cantine/models/lagunes_plat_option.py#L57-L63)
— Ajout du champ + contrainte unique par société.

### 17. API `/cantine/api/options` sans validation session
**Fichier**: [api.py](file:///C:/odoo18/custom_addons/lagunes_cantine/controllers/api.py#L16-L39)
— Ajout validation session + filtrage `company_id`.

---

## 📋 Phase 4 — Tests, Scripts & Documentation

### 18. Audit logging
**Fichier**: [main.py](file:///C:/odoo18/custom_addons/lagunes_cantine/controllers/main.py#L7-L74)
— `_logger.warning` pour IP bloquées, `_logger.info` pour connexions réussies.

### 19. CSRF documentation
**Fichier**: [api.py](file:///C:/odoo18/custom_addons/lagunes_cantine/controllers/api.py#L16-L19)
— Commentaire explicatif sur la sécurité JSON-RPC.

### 20. Rate limiter production note
**Fichier**: [main.py](file:///C:/odoo18/custom_addons/lagunes_cantine/controllers/main.py#L32-L35)
— Warning sur les limitations in-memory.

### 21. Script pre-migration (doublons)
**Fichier**: [pre_migrate_clean_duplicates.py](file:///C:/odoo18/custom_addons/lagunes_cantine/scripts/pre_migrate_clean_duplicates.py)
— Nettoyage des doublons `lagunes_week_menu_line` et `lagunes_plat_option` avant upgrade.

### 22-24. Suite de tests
**Fichiers**:
- [test_security.py](file:///C:/odoo18/custom_addons/lagunes_cantine/tests/test_security.py) — 7 tests (password bypass, ACL, rate limiting, session type safety, record rules)
- [test_stock.py](file:///C:/odoo18/custom_addons/lagunes_cantine/tests/test_stock.py) — 8 tests (_remove_quantity API, capped, idempotence, action_cancel)

---

## 📁 Fichiers modifiés — Récapitulatif complet

| Module | Fichier | Correctifs |
|--------|---------|-----------|
| `lagunes_cantine` | `models/lagunes_employe.py` | #1 |
| | `models/res_partner.py` | #3 |
| | `models/lagunes_commande.py` | #10 |
| | `models/lagunes_week_menu.py` | #8, #14 |
| | `models/lagunes_facturation_periode.py` | #9 |
| | `models/lagunes_dashboard.py` | #12 |
| | `models/lagunes_plat_option.py` | #11, #16 |
| | `controllers/main.py` | #4, #18, #20 |
| | `controllers/api.py` | #13, #17, #19 |
| | `controllers/week_menu.py` | Session fixes |
| | `security/ir.model.access.csv` | #2 |
| | `security/lagunes_security.xml` | #5 |
| | `scripts/pre_migrate_clean_duplicates.py` | #21 (nouveau) |
| | `tests/test_security.py` | #22 (nouveau) |
| | `tests/test_stock.py` | #23-24 (nouveau) |
| `lagunes_market` | `models/lagunes_market.py` | #6, #7 |
| | `models/lagunes_market_stock.py` | #15 |

---

## 🚀 Procédure de déploiement

```bash
# 1. Exécuter le script de nettoyage des doublons
python odoo-bin shell -d <database> < custom_addons/lagunes_cantine/scripts/pre_migrate_clean_duplicates.py

# 2. Mettre à jour les modules
python odoo-bin -d <database> -u lagunes_cantine,lagunes_market --stop-after-init

# 3. Lancer les tests
python odoo-bin -d <database> --test-tags lagunes_security,lagunes_stock --stop-after-init
```

> [!IMPORTANT]
> L'étape 1 est **obligatoire** avant le upgrade. Les nouvelles contraintes SQL (`unique(week_menu_id, day, plat_type_id)` et `unique(name, company_id)`) échoueront si des doublons existent.
