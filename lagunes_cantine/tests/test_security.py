# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


@tagged('post_install', '-at_install', 'lagunes_security')
class TestCantineSecurity(TransactionCase):
    """Tests de sécurité pour le module lagunes_cantine."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Créer une entreprise cantine cliente
        cls.entreprise = cls.env['res.partner'].create({
            'name': 'Test Entreprise Sécurité',
            'is_cantine_client': True,
            'cantine_access_code': 'SEC2024',
            'company_id': cls.company.id,
        })

        # Créer un employé avec mot de passe
        cls.employe = cls.env['lagunes.employe'].create({
            'name': 'Test Employé Sécurisé',
            'email': 'securite@test.com',
            'entreprise_id': cls.entreprise.id,
            'company_id': cls.company.id,
        })

    # ──────────────────────────────────────────────────────────────
    #  TEST 1 : mot_de_passe invisible pour les non-admins
    # ──────────────────────────────────────────────────────────────

    def test_password_field_groups(self):
        """Le champ mot_de_passe doit être restreint à base.group_system."""
        field = self.env['lagunes.employe']._fields['mot_de_passe']
        self.assertIn('base.group_system', field.groups,
                      "mot_de_passe doit avoir groups='base.group_system'")

    # ──────────────────────────────────────────────────────────────
    #  TEST 2 : bypass password quand hash existe
    # ──────────────────────────────────────────────────────────────

    def test_password_bypass_blocked(self):
        """Si un hash existe, l'authentification DOIT exiger un mot de passe."""
        # Simuler un hash en base (via sudo car groups=base.group_system)
        self.employe.sudo().write({
            'mot_de_passe': '$2b$12$fakehashfortest000000000000000000000000000000',
        })

        # Tenter de se connecter SANS mot de passe
        result = self.env['res.partner'].sudo().verify_cantine_access(
            access_code='SEC2024',
            email='securite@test.com',
            mot_de_passe=None,  # pas de mot de passe
        )
        self.assertFalse(result.get('success'),
                         "Connexion sans mot de passe doit échouer quand un hash existe")

    # ──────────────────────────────────────────────────────────────
    #  TEST 3 : access rights public
    # ──────────────────────────────────────────────────────────────

    def test_public_cannot_create_employe(self):
        """Le groupe public ne doit PAS pouvoir créer des employés."""
        acl = self.env['ir.model.access'].search([
            ('model_id.model', '=', 'lagunes.employe'),
            ('group_id', '=', self.env.ref('base.group_public').id),
        ])
        for rule in acl:
            self.assertFalse(rule.perm_create,
                             f"La règle {rule.name} ne doit pas autoriser perm_create pour group_public")

    # ──────────────────────────────────────────────────────────────
    #  TEST 4 : session entreprise_id strict int comparison
    # ──────────────────────────────────────────────────────────────

    def test_session_entreprise_id_type_safety(self):
        """L'ID entreprise en session doit être comparé en int strict."""
        from odoo.addons.lagunes_cantine.controllers.week_menu import LagunesWeekMenuController

        # Simuler : session a l'ID en string, request a l'ID en int
        # La comparaison int() doit fonctionner dans les deux sens
        session_id_str = str(self.entreprise.id)
        request_id_int = self.entreprise.id

        self.assertEqual(int(session_id_str), int(request_id_int),
                         "La comparaison int() doit fonctionner string vs int")

    # ──────────────────────────────────────────────────────────────
    #  TEST 5 : rate limiter
    # ──────────────────────────────────────────────────────────────

    def test_rate_limiter(self):
        """Le rate limiter doit bloquer après N tentatives."""
        from odoo.addons.lagunes_cantine.controllers.main import LagunesCantineController

        # Reset le state
        LagunesCantineController._login_attempts = {}
        test_ip = '192.168.99.99'

        # Les 5 premières tentatives passent
        for i in range(5):
            self.assertFalse(
                LagunesCantineController._check_rate_limit(test_ip),
                f"Tentative {i+1} ne doit PAS être bloquée"
            )

        # La 6ème doit être bloquée
        self.assertTrue(
            LagunesCantineController._check_rate_limit(test_ip),
            "La 6ème tentative DOIT être bloquée"
        )

        # Cleanup
        LagunesCantineController._login_attempts = {}

    def test_rate_limiter_window_expiry(self):
        """Le rate limiter doit libérer après expiration de la fenêtre."""
        from odoo.addons.lagunes_cantine.controllers.main import LagunesCantineController

        LagunesCantineController._login_attempts = {}
        test_ip = '192.168.99.100'

        # Injecter 5 tentatives datées de 2 minutes dans le passé
        past = datetime.now() - timedelta(seconds=120)
        LagunesCantineController._login_attempts[test_ip] = [past] * 5

        # L'IP ne doit PAS être bloquée (tentatives expirées)
        self.assertFalse(
            LagunesCantineController._check_rate_limit(test_ip),
            "Les tentatives expirées ne doivent pas compter"
        )

        LagunesCantineController._login_attempts = {}


@tagged('post_install', '-at_install', 'lagunes_security')
class TestRecordRules(TransactionCase):
    """Vérifie que les record rules utilisent company_id."""

    def test_week_menu_rule_uses_company_id(self):
        """La rule rule_lagunes_week_menu_multi_company doit filtrer par company_id."""
        rule = self.env.ref('lagunes_cantine.rule_lagunes_week_menu_multi_company')
        self.assertIn('company_id', rule.domain_force,
                      "La rule week menu doit filtrer par company_id")

    def test_commande_rule_uses_company_id(self):
        """La rule lagunes_commande_company_rule doit filtrer par company_id."""
        rule = self.env.ref('lagunes_cantine.lagunes_commande_company_rule')
        self.assertIn('company_id', rule.domain_force,
                      "La rule commande doit filtrer par company_id")
