# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LaguesPlatIngredient(models.Model):
    """Ingrédients nécessaires pour un plat"""
    
    _name = 'lagunes.plat.ingredient'
    _description = 'Ingrédient d\'un plat'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'plat_id, sequence'
    
    plat_id = fields.Many2one(
        'lagunes.plat',
        string='Plat',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    # Article du marché
    market_article_id = fields.Many2one(
        'lagunes.market.article',
        string='Article du marché',
        required=True,
        ondelete='restrict',
        tracking=True
    )
    
    # Quantité
    quantity = fields.Float(
        string='Quantité nécessaire',
        required=True,
        default=1.0,
        tracking=True
    )
    
    # Unité (kg, litre, etc.)
    unit_id = fields.Many2one(
        'lagunes.market.uom',
        string='Unité',
        required=True,
    )
    
    # Ingrédient quantifiable (pour déduction automatique du stock)
    is_quantifiable = fields.Boolean(
        string='Quantifiable',
        default=True,
        help='Si coché, la quantité sera déduite du stock du marché',
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10,
        tracking=True
    )
    
    notes = fields.Text(
        string='Notes',
        help='Notes sur l\'utilisation de cet ingrédient'
    )

    @api.onchange('market_article_id')
    def _onchange_market_article_id(self):
        if self.market_article_id:
            # Proposer l'unité par défaut de l'article
            self.unit_id = self.market_article_id.default_uom_id
            
            # Retourner domaine restreint + message d'info
            return {
                'domain': {'unit_id': [('category_id', '=', self.market_article_id.default_uom_id.category_id.id)]},
                'warning': {
                    'title': _('Article sélectionné'),
                    'message': _(
                        "Article: %s\n"
                        "Unité de stock: %s (catégorie: %s)\n\n"
                        "⚠️ Vous ne pourrez sélectionner que des unités de la même catégorie."
                    ) % (
                        self.market_article_id.name,
                        self.market_article_id.default_uom_id.name,
                        self.market_article_id.default_uom_id.category_id.name
                    )
                }
            }
        return {'domain': {'unit_id': []}}

    @api.constrains('unit_id', 'market_article_id')
    def _check_uom_category(self):
        for ingredient in self:
            if ingredient.unit_id and ingredient.market_article_id:
                if ingredient.unit_id.category_id != ingredient.market_article_id.default_uom_id.category_id:
                    raise ValidationError(_(
                        "L'unité '%s' n'est pas compatible avec l'unité d'origine de l'article '%s' (%s). "
                        "Les deux doivent appartenir à la même catégorie (ex: Poids, Volume)."
                    ) % (
                        ingredient.unit_id.name,
                        ingredient.market_article_id.name,
                        ingredient.market_article_id.default_uom_id.name
                    ))

    @api.constrains('plat_id', 'market_article_id')
    def _check_company_consistency(self):
        for ingredient in self:
            if not ingredient.plat_id.company_id or not ingredient.market_article_id:
                continue

            stock_exists = self.env['lagunes.market.stock'].sudo().search_count([
                ('article_id', '=', ingredient.market_article_id.id),
                ('company_id', '=', ingredient.plat_id.company_id.id),
            ])
            if not stock_exists:
                raise ValidationError(_(
                    "L'article '%(article)s' n'a pas de stock initial dans la société '%(company)s'. "
                    "Créez d'abord une ligne de stock pour cette société."
                ) % {
                    'article': ingredient.market_article_id.name,
                    'company': ingredient.plat_id.company_id.name,
                })
    
    # Coût unitaire (depuis le marché)
    article_unit_price = fields.Float(
        string='Prix unitaire article',
        readonly=True,
        compute='_compute_article_unit_price',
        store=True,
    )
    
    # Coût pour cette portion
    ingredient_cost = fields.Float(
        string='Coût par portion',
        compute='_compute_ingredient_cost',
        store=True
    )
    
    @api.depends('market_article_id')
    def _compute_article_unit_price(self):
        for ingredient in self:
            if not ingredient.market_article_id:
                ingredient.article_unit_price = 0.0
                continue

            last_line = self.env['lagunes.market.line'].search(
                [
                    ('article_id', '=', ingredient.market_article_id.id),
                    ('market_id.state', '=', 'validated'),
                ],
                order='market_id desc, id desc',
                limit=1,
            )
            ingredient.article_unit_price = last_line.unit_price if last_line else 0.0

    @api.depends('quantity', 'article_unit_price', 'is_quantifiable', 'unit_id', 'market_article_id.default_uom_id')
    def _compute_ingredient_cost(self):
        for ingredient in self:
            if ingredient.is_quantifiable and ingredient.market_article_id and ingredient.unit_id:
                # Utilise le helper du module marché pour convertir
                qty_stock = ingredient.unit_id.compute_quantity(
                    ingredient.quantity, 
                    ingredient.market_article_id.default_uom_id
                )
                ingredient.ingredient_cost = qty_stock * ingredient.article_unit_price
            else:
                ingredient.ingredient_cost = 0.0
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for ingredient in self:
            if ingredient.quantity <= 0:
                raise ValidationError(
                    _('La quantité doit être strictement positive pour "%s"') % ingredient.market_article_id.name
                )
    
    _sql_constraints = [
        ('unique_plat_article', 'unique(plat_id, market_article_id)', 
         'Un ingrédient ne peut être ajouté qu\'une seule fois par plat'),
    ]
