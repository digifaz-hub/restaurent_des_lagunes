# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LagunesMarketLine(models.Model):
    """Ligne d'article pour un marché d'approvisionnement.
    Chaque ligne représente un article acheté lors d'une sortie au marché.
    """
    _name = 'lagunes.market.line'
    _description = 'Ligne d\'article de marché'
    _order = 'sequence asc, id asc'

    market_id = fields.Many2one(
        comodel_name='lagunes.market',
        string='Marché',
        required=True,
        ondelete='cascade',
    )
    market_date = fields.Date(
        string='Date du marché',
        related='market_id.date',
        store=True,
        index=True,
    )
    sequence = fields.Integer(
        string='Séquence',
        default=10,
        help='Ordre d\'affichage des lignes',
    )
    article_id = fields.Many2one(
        comodel_name='lagunes.market.article',
        string='Article',
        required=True,
        ondelete='restrict',
    )
    category_id = fields.Many2one(
        comodel_name='lagunes.market.article.category',
        string='Catégorie',
        related='article_id.category_id',
        store=True,
    )
    qty = fields.Float(
        string='Quantité',
        required=True,
        default=1.0,
        digits=(16, 3),
    )

    unit_price = fields.Float(
        string='Prix unitaire',
        digits=(16, 3),
        default=0.0,
    )

    subtotal = fields.Float(
        string='Sous-total',
        compute='_compute_subtotal',
        store=True,
        digits=(16, 3),
    )
    uom_id = fields.Many2one(
        comodel_name='lagunes.market.uom',
        string='Unité',
        ondelete='restrict',
        help='Unité de mesure (pré-remplie depuis l\'article, modifiable)',
    )
    # Champ texte calculé pour compatibilité rapport/stock
    uom = fields.Char(
        string='Unité (texte)',
        compute='_compute_uom',
        store=True,
    )

    stock_before = fields.Float(
        string='Stock avant achat',
        digits=(16, 3),
        readonly=True,
        default=0.0,
        store=True,
        copy=False,
        help='Quantité en stock au moment de la validation du marché (snapshot figé).',
    )
    stock_after = fields.Float(
        string='Stock après',
        compute='_compute_stock_after',
        digits=(16, 3),
        help='Projection du stock après validation de cet achat (Stock avant + Quantité)',
    )

    @api.depends('qty', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = (line.qty or 0.0) * (line.unit_price or 0.0)
    
    @api.depends('stock_before', 'qty')
    def _compute_stock_after(self):
        for line in self:
            line.stock_after = line.stock_before + line.qty
    
    @api.constrains('qty')
    def _check_qty_positive(self):
        for line in self:
            if line.qty <= 0:
                raise ValidationError(_("La quantité doit être strictement positive pour l'article '%s'.") % line.article_id.name)

    _sql_constraints = [
        ('market_article_uniq', 'unique(market_id, article_id)', 
         'Cet article est déjà présent dans les lignes de ce marché.'),
    ]

    @api.depends('uom_id')
    def _compute_uom(self):
        for line in self:
            line.uom = line.uom_id.name or ''


    @api.onchange('article_id')
    def _onchange_article_id(self):
        """Pré-remplit l'unité et la catégorie dès la sélection de l'article en UI."""
        if self.article_id:
            self.uom_id = self.article_id.default_uom_id
            stock = self.env['lagunes.market.stock'].search(
                [('article_id', '=', self.article_id.id)], limit=1
            )
            self.stock_before = stock.qty if stock else 0.0
            self.unit_price = 0.0
        else:
            self.uom_id = False
            self.stock_before = 0.0
            self.unit_price = 0.0