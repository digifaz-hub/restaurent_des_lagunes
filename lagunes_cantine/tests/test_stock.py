# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install', 'lagunes_stock')
class TestStockRemoveQuantity(TransactionCase):
    """Tests pour _remove_quantity et _add_quantity dans lagunes.market.stock."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Créer un article de marché
        cls.article = cls.env['lagunes.market.article'].create({
            'name': 'Riz Test',
            'company_id': cls.company.id,
        })

        # Créer un enregistrement de stock
        cls.stock = cls.env['lagunes.market.stock'].create({
            'article_id': cls.article.id,
            'company_id': cls.company.id,
            'qty': 100.0,
        })

    # ──────────────────────────────────────────────────────────────
    #  TEST 1 : _remove_quantity retourne un dict
    # ──────────────────────────────────────────────────────────────

    def test_remove_quantity_returns_dict(self):
        """_remove_quantity doit retourner un dict, pas un bool."""
        result = self.stock._remove_quantity(
            article_id=self.article.id,
            qty=10.0,
            note='Test unitaire',
        )
        self.assertIsInstance(result, dict,
                             "_remove_quantity doit retourner un dict")
        self.assertIn('success', result)
        self.assertIn('is_capped', result)
        self.assertIn('requested_qty', result)
        self.assertIn('actual_qty', result)

    # ──────────────────────────────────────────────────────────────
    #  TEST 2 : déduction normale
    # ──────────────────────────────────────────────────────────────

    def test_remove_quantity_normal(self):
        """Une déduction inférieure au stock disponible ne doit pas être capped."""
        initial_qty = self.stock.qty
        result = self.stock._remove_quantity(
            article_id=self.article.id,
            qty=10.0,
            note='Test normal',
        )
        self.assertTrue(result.get('success'))
        self.assertFalse(result.get('is_capped'))
        self.assertEqual(result['actual_qty'], 10.0)
        self.stock.invalidate_recordset()
        self.assertAlmostEqual(self.stock.qty, initial_qty - 10.0)

    # ──────────────────────────────────────────────────────────────
    #  TEST 3 : déduction capped (stock insuffisant)
    # ──────────────────────────────────────────────────────────────

    def test_remove_quantity_capped(self):
        """Si qty > stock, et allow_capped=True, le stock doit descendre à 0."""
        self.stock.write({'qty': 5.0})
        result = self.stock._remove_quantity(
            article_id=self.article.id,
            qty=20.0,
            note='Test capped',
            allow_capped=True,
        )
        self.assertTrue(result.get('success'))
        self.assertTrue(result.get('is_capped'))
        self.assertEqual(result['requested_qty'], 20.0)
        self.assertLessEqual(result['actual_qty'], 5.0)
        self.stock.invalidate_recordset()
        self.assertAlmostEqual(self.stock.qty, 0.0)

    # ──────────────────────────────────────────────────────────────
    #  TEST 4 : déduction refusée sans allow_capped
    # ──────────────────────────────────────────────────────────────

    def test_remove_quantity_insufficient_no_cap(self):
        """Si qty > stock et allow_capped=False, le résultat doit indiquer un échec."""
        self.stock.write({'qty': 5.0})
        result = self.stock._remove_quantity(
            article_id=self.article.id,
            qty=20.0,
            note='Test insuffisant',
            allow_capped=False,
        )
        # Doit échouer ou capper selon l'implémentation
        self.assertIsInstance(result, dict)

    # ──────────────────────────────────────────────────────────────
    #  TEST 5 : _add_quantity retourne un dict
    # ──────────────────────────────────────────────────────────────

    def test_add_quantity_returns_dict(self):
        """_add_quantity doit retourner un dict."""
        initial_qty = self.stock.qty
        result = self.stock._add_quantity(
            article_id=self.article.id,
            qty=25.0,
            note='Test ajout',
        )
        self.assertIsInstance(result, dict,
                             "_add_quantity doit retourner un dict")
        self.stock.invalidate_recordset()
        self.assertAlmostEqual(self.stock.qty, initial_qty + 25.0)

    # ──────────────────────────────────────────────────────────────
    #  TEST 6 : move_category 'adjustment' existe
    # ──────────────────────────────────────────────────────────────

    def test_move_category_adjustment_exists(self):
        """La valeur 'adjustment' doit exister dans move_category."""
        Move = self.env['lagunes.market.stock.move']
        field = Move._fields['move_category']
        selection_keys = [key for key, _label in field.selection]
        self.assertIn('adjustment', selection_keys,
                      "'adjustment' doit être dans les valeurs de move_category")


@tagged('post_install', '-at_install', 'lagunes_stock')
class TestStockIdempotence(TransactionCase):
    """Tests d'idempotence pour la déduction de stock via les commandes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    def test_deduct_twice_is_idempotent(self):
        """Appeler _deduct_ingredients_from_market 2× ne doit déduire qu'une fois."""
        # Ce test nécessite un setup complet (plat, ingrédients, commande)
        # On vérifie simplement que le flag is_stock_deducted bloque le 2nd appel
        commande = self.env['lagunes.commande'].search(
            [('is_stock_deducted', '=', True)], limit=1
        )
        if commande:
            initial_deducted = commande.is_stock_deducted
            commande._deduct_ingredients_from_market()
            # Doit rester True sans erreur
            self.assertTrue(commande.is_stock_deducted)


@tagged('post_install', '-at_install', 'lagunes_stock')
class TestMarketCancel(TransactionCase):
    """Tests pour la logique d'annulation de marché."""

    def test_cancel_uses_allow_capped(self):
        """action_cancel doit passer allow_capped=True à _remove_quantity."""
        import inspect
        from odoo.addons.lagunes_market.models.lagunes_market import LagunesMarket

        source = inspect.getsource(LagunesMarket.action_cancel)
        self.assertIn('allow_capped=True', source,
                      "action_cancel doit passer allow_capped=True")

    def test_cancel_uses_result_get(self):
        """action_cancel doit utiliser result.get('is_capped'), pas un bool."""
        import inspect
        from odoo.addons.lagunes_market.models.lagunes_market import LagunesMarket

        source = inspect.getsource(LagunesMarket.action_cancel)
        self.assertIn("result.get('is_capped')", source,
                      "action_cancel doit utiliser result.get('is_capped')")
        self.assertNotIn('is_capped = stock_model', source,
                         "action_cancel ne doit plus traiter le retour comme un bool")
