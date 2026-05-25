# -*- coding: utf-8 -*-
"""
Initialisation des identifiants de démonstration pour la cantine.

Ce script est exécuté à chaque chargement des données de démo et initialise:
- Les mots de passe des employés (demo123 par défaut)
- Les codes d'accès des entreprises (basés sur le nom de l'entreprise)

Le script est idempotent: il ne modifie que les valeurs vides/non définies.
"""

from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """Initialise les identifiants de démo."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Mot de passe par défaut pour les employés de démo
    DEFAULT_EMPLOYEE_PASSWORD = "demo123"
    
    # Initialiser les mots de passe employés
    cr.execute("""
        SELECT id FROM lagunes_employe 
        WHERE mot_de_passe IS NULL OR mot_de_passe = ''
    """)
    emp_ids = [row[0] for row in cr.fetchall()]
    
    if emp_ids:
        env['lagunes.employe'].browse(emp_ids)._set_password(DEFAULT_EMPLOYEE_PASSWORD)
        print(f"[Lagunes Cantine] {len(emp_ids)} mot(s) de passe employé initialisé(s)")
    
    # Initialiser les codes d'accès entreprise (via ORM pour éviter les conflits de contraintes)
    companies = env['res.partner'].search([
        ('is_cantine_client', '=', True),
        '|',
        ('cantine_access_code', '=', False),
        ('cantine_access_code', '=', ''),
    ])
    
    for company in companies:
        # Générer un code basé sur le nom de l'entreprise
        code_base = company.name.upper().replace(' ', '').replace('É', 'E').replace('È', 'E').replace('Ô', 'O')
        access_code = f"{code_base}2026"
        
        company.cantine_access_code = access_code
        print(f"[Lagunes Cantine] Code d'accès initialisé pour {company.name}: {access_code}")
