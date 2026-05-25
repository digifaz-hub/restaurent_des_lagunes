# -*- coding: utf-8 -*-
"""
Script de nettoyage pre-migration : supprime les doublons
(week_menu_id, day, plat_type_id) dans lagunes_week_menu_line
AVANT l'ajout de la contrainte SQL unique.

Usage : exécuter ce script via `odoo shell` AVANT le `-u lagunes_cantine`

    python odoo-bin shell -d <database> < custom_addons/lagunes_cantine/scripts/pre_migrate_clean_duplicates.py
"""

def clean_week_menu_line_duplicates(env):
    """Supprime les doublons (week_menu_id, day, plat_type_id),
    en gardant la ligne la plus récente (id le plus élevé)."""
    cr = env.cr

    # Étape 1 : Identifier les groupes de doublons
    cr.execute("""
        SELECT week_menu_id, day, plat_type_id, COUNT(*) as cnt,
               array_agg(id ORDER BY id DESC) as ids
        FROM lagunes_week_menu_line
        GROUP BY week_menu_id, day, plat_type_id
        HAVING COUNT(*) > 1
    """)
    duplicates = cr.fetchall()

    if not duplicates:
        print("✅ Aucun doublon trouvé dans lagunes_week_menu_line.")
        return

    total_deleted = 0
    for week_menu_id, day, plat_type_id, count, ids in duplicates:
        # Garder le premier (id le plus élevé), supprimer les autres
        keep_id = ids[0]
        delete_ids = ids[1:]
        print(f"  🔧 Menu {week_menu_id}, jour {day}, type {plat_type_id}: "
              f"{count} doublons → garde #{keep_id}, supprime {delete_ids}")
        cr.execute(
            "DELETE FROM lagunes_week_menu_line WHERE id IN %s",
            (tuple(delete_ids),)
        )
        total_deleted += len(delete_ids)

    env.cr.commit()
    print(f"\n✅ {total_deleted} doublon(s) supprimé(s). La contrainte unique peut maintenant être appliquée.")


def clean_plat_option_duplicates(env):
    """Supprime les doublons (name, company_id) dans lagunes_plat_option
    avant l'ajout de la contrainte unique per-company."""
    cr = env.cr

    cr.execute("""
        SELECT name, company_id, COUNT(*) as cnt,
               array_agg(id ORDER BY id DESC) as ids
        FROM lagunes_plat_option
        GROUP BY name, company_id
        HAVING COUNT(*) > 1
    """)
    duplicates = cr.fetchall()

    if not duplicates:
        print("✅ Aucun doublon trouvé dans lagunes_plat_option.")
        return

    total_deleted = 0
    for name, company_id, count, ids in duplicates:
        keep_id = ids[0]
        delete_ids = ids[1:]
        print(f"  🔧 Option '{name}' (company {company_id}): "
              f"{count} doublons → garde #{keep_id}, supprime {delete_ids}")
        cr.execute(
            "DELETE FROM lagunes_plat_option WHERE id IN %s",
            (tuple(delete_ids),)
        )
        total_deleted += len(delete_ids)

    env.cr.commit()
    print(f"\n✅ {total_deleted} doublon(s) d'options supprimé(s).")


# Point d'entrée pour odoo shell
if __name__ == '__main__':
    # `env` est disponible automatiquement dans odoo shell
    print("=" * 60)
    print("  PRE-MIGRATION : Nettoyage des doublons")
    print("=" * 60)
    print("\n1/2 — lagunes_week_menu_line...")
    clean_week_menu_line_duplicates(env)  # noqa: F821
    print("\n2/2 — lagunes_plat_option...")
    clean_plat_option_duplicates(env)  # noqa: F821
    print("\n" + "=" * 60)
    print("  Terminé. Vous pouvez maintenant lancer -u lagunes_cantine")
    print("=" * 60)
