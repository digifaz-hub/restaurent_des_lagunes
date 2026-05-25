# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LagunesMarketLeftover(models.Model):
    """Ligne de stock initial : article non consommé depuis le marché précédent."""
    _name = 'lagunes.market.leftover'
    _description = 'Stock initial du marché précédent'
    _order = 'sequence asc, id asc'

    market_id = fields.Many2one(
        comodel_name='lagunes.market',
        string='Marché',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Séquence', default=10)

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
    uom_id = fields.Many2one(
        comodel_name='lagunes.market.uom',
        string='Unité',
        ondelete='restrict',
        help='Unité de mesure (pré-remplie depuis l\'article)',
    )
    # Champ texte calculé pour compatibilité rapport/stock
    uom = fields.Char(
        string='Unité (texte)',
        compute='_compute_uom',
        store=True,
    )

    stock_current = fields.Float(
        string='Stock actuel',
        compute='_compute_stock_current',
        store=True,
        readonly=True,
        digits=(16, 3),
        help='Stock disponible au moment de la saisie (avant ce marché)',
    )

    qty_remaining = fields.Float(
        string='Quantité restante',
        required=True,
        default=0.0,
        digits=(16, 3),
        help='Quantité non consommée depuis le dernier marché.',
    )

    @api.constrains('qty_remaining')
    def _check_qty_remaining_non_negative(self):
        for leftover in self:
            if leftover.qty_remaining < 0:
                raise ValidationError(_("La quantité restante ne peut pas être négative pour l'article '%s'.") % leftover.article_id.name)

    _sql_constraints = [
        ('market_article_uniq', 'unique(market_id, article_id)', 
         'Cet article est déjà présent dans les reliquats de ce marché.'),
    ]

    @api.depends('uom_id')
    def _compute_uom(self):
        for line in self:
            line.uom = line.uom_id.name or ''

    @api.depends('article_id')
    def _compute_stock_current(self):
        for line in self:
            if line.article_id:
                stock = self.env['lagunes.market.stock'].search(
                    [('article_id', '=', line.article_id.id)], limit=1
                )
                line.stock_current = stock.qty if stock else 0.0
            else:
                line.stock_current = 0.0

    @api.onchange('article_id')
    def _onchange_article_id(self):
        if self.article_id:
            self.uom_id = self.article_id.default_uom_id
            stock = self.env['lagunes.market.stock'].search(
                [('article_id', '=', self.article_id.id)], limit=1
            )
            self.qty_remaining = stock.qty if stock else 0.0
        else:
            self.uom_id = False
            self.qty_remaining = 0.0