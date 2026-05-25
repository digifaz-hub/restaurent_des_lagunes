# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class LagunesMarketArticleCategory(models.Model):
    """Catégories d'articles du marché (légumes, viandes, céréales...).
    Permet de regrouper les articles pour une meilleure lisibilité.
    """
    _name = 'lagunes.market.article.category'
    _description = 'Catégorie d\'article de marché'
    _order = 'name asc'

    name = fields.Char(
        string='Nom',
        required=True,
        translate=True,
    )
    active = fields.Boolean(
        string='Actif',
        default=True,
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Le nom de la catégorie doit être unique.'),
    ]


class LagunesMarketArticle(models.Model):
    """Catalogue interne des articles achetés au marché.
    Indépendant de product.product — géré entièrement dans ce module.
    """
    _name = 'lagunes.market.article'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Article de marché'
    _order = 'name asc'

    name = fields.Char(
        string='Nom',
        required=True,
        tracking=True,
    )
    category_id = fields.Many2one(
        comodel_name='lagunes.market.article.category',
        string='Catégorie',
        ondelete='restrict',
        tracking=True,
    )
    default_uom_id = fields.Many2one(
        comodel_name='lagunes.market.uom',
        string='Unité de mesure',
        ondelete='restrict',
        help='Unité de mesure par défaut (kg, pièce, litre, botte…)',
        tracking=True,
    )
    # Compatibilité ascendante : champ texte calculé depuis default_uom_id
    default_uom = fields.Char(
        string='Unité (texte)',
        compute='_compute_default_uom',
        store=True,
        help='Nom de l\'unité de mesure (calculé depuis default_uom_id)',
    )
    # Champ calculé : stock disponible actuel depuis lagunes.market.stock
    stock_qty = fields.Float(
        string='Stock disponible',
        compute='_compute_stock_qty',
        store=False,
        help='Quantité actuellement en stock (calculée depuis le stock interne)',
    )
    active = fields.Boolean(
        string='Actif',
        default=True,
        help='Désactiver pour archiver l\'article sans le supprimer',
    )
    market_line_count = fields.Integer(
        string='Nombre d\'achats',
        compute='_compute_market_line_count',
    )
    reorder_point = fields.Float(
        string='Seuil minimal',
        compute='_compute_reorder_point',
        inverse='_inverse_reorder_point',
        help='Seuil de réapprovisionnement pour la société courante.',
    )
    last_purchase_price = fields.Float(string='Dernier prix d\'achat', compute='_compute_last_purchase_price')
    price_history_json = fields.Text(string='Historique des Prix (JSON)', compute='_compute_price_history_json')

    def _compute_last_purchase_price(self):
        for rec in self:
            last_line = self.env['lagunes.market.line'].search([
                ('article_id', '=', rec.id),
                ('market_id.state', '=', 'validated')
            ], order='market_date desc', limit=1)
            rec.last_purchase_price = last_line.unit_price if last_line else 0.0

    def _compute_price_history_json(self):
        import json
        for rec in self:
            history = []
            purchases = self.env['lagunes.market.line'].search([
                ('article_id', '=', rec.id),
                ('market_id.state', '=', 'validated')
            ], order='market_date asc', limit=20)
            for p in purchases:
                history.append({
                    'date': p.market_date.strftime('%d/%m/%Y') if p.market_date else '',
                    'price': p.unit_price
                })
            rec.price_history_json = json.dumps(history)


    def _compute_market_line_count(self):
        for article in self:
            article.market_line_count = self.env['lagunes.market.line'].search_count(
                [('article_id', '=', article.id)]
            )

    def action_view_market_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Historique des achats : %s') % self.name,
            'res_model': 'lagunes.market.line',
            'view_mode': 'list,form',
            'domain': [('article_id', '=', self.id)],
            'context': {'search_default_group_market': 1},
        }

    def action_view_stock_moves(self):
        """Ouvre la liste des mouvements de stock pour cet article."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mouvements de stock : %s') % self.name,
            'res_model': 'lagunes.market.stock.move',
            'view_mode': 'list,form',
            'domain': [('article_id', '=', self.id)],
            'context': {'search_default_group_date': 1},
        }

    @api.depends('default_uom_id')
    def _compute_default_uom(self):
        for article in self:
            article.default_uom = article.default_uom_id.name or ''

    def _compute_stock_qty(self):
        """Calcule la quantité en stock depuis le modèle lagunes.market.stock."""
        for article in self:
            stock = self.env['lagunes.market.stock'].search(
                [('article_id', '=', article.id), ('company_id', '=', self.env.company.id)], limit=1
            )
            article.stock_qty = stock.qty if stock else 0.0

    def _compute_reorder_point(self):
        """Récupère le seuil minimal depuis le modèle lagunes.market.stock."""
        for article in self:
            stock = self.env['lagunes.market.stock'].search(
                [('article_id', '=', article.id), ('company_id', '=', self.env.company.id)], limit=1
            )
            article.reorder_point = stock.reorder_point if stock else 0.0

    def _inverse_reorder_point(self):
        """Met à jour le seuil minimal dans le modèle lagunes.market.stock."""
        for article in self:
            stock = self.env['lagunes.market.stock'].search(
                [('article_id', '=', article.id), ('company_id', '=', self.env.company.id)], limit=1
            )
            if stock:
                stock.reorder_point = article.reorder_point
            else:
                self.env['lagunes.market.stock'].create({
                    'article_id': article.id,
                    'reorder_point': article.reorder_point,
                    'company_id': self.env.company.id,
                })

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Le nom de l\'article doit être unique.'),
    ]
