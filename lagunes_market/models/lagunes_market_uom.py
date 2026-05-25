# -*- coding: utf-8 -*-
from odoo import fields, models, api


class LagunesMarketUomCategory(models.Model):
    """Catégories d'unités de mesure (Poids, Volume, Unité, etc.)"""
    _name = 'lagunes.market.uom.category'
    _description = 'Catégorie d\'unité (marché)'
    _order = 'name asc'

    name = fields.Char(string='Catégorie', required=True, translate=True)


class LagunesMarketUom(models.Model):
    """Unités de mesure utilisées dans le module marché."""
    _name = 'lagunes.market.uom'
    _description = 'Unité de mesure (marché)'
    _order = 'category_id, name'

    name = fields.Char(
        string='Unité',
        required=True,
        translate=True,
    )
    category_id = fields.Many2one(
        'lagunes.market.uom.category',
        string='Catégorie',
        required=True,
        ondelete='cascade',
    )
    uom_type = fields.Selection([
        ('reference', 'Unité de référence de la catégorie'),
        ('smaller', 'Plus petite que l\'unité de référence'),
        ('bigger', 'Plus grande que l\'unité de référence'),
    ], string='Type d\'unité', default='reference', required=True)

    factor = fields.Float(
        string='Ratio',
        default=1.0,
        required=True,
        help='Ratio par rapport à l\'unité de référence'
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True,
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Le nom de l\'unité doit être unique.'),
    ]

    @api.onchange('uom_type')
    def _onchange_uom_type(self):
        if self.uom_type == 'reference':
            self.factor = 1.0

    def compute_quantity(self, qty, to_uom, raise_if_incompatible=False):
        """Convertit 'qty' de l'unité actuelle vers 'to_uom'

        Args:
            qty: Quantité à convertir
            to_uom: Unité de destination
            raise_if_incompatible: Si True, lève une erreur si catégories incompatibles

        Returns:
            Quantité convertie (ou qty inchangé si incompatible et raise_if_incompatible=False)
        """
        self.ensure_one()
        if not to_uom:
            return qty

        # Vérification catégorie
        if self.category_id != to_uom.category_id:
            msg = (
                f"Conversion impossible : {self.name} (catégorie: {self.category_id.name}) "
                f"vers {to_uom.name} (catégorie: {to_uom.category_id.name})"
            )
            if raise_if_incompatible:
                raise ValueError(msg)
            # Log warning pour traçabilité
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(msg + f" - Quantité {qty} retournée sans conversion")
            return qty
        
        # 1. Normalisation vers l'unité de référence
        if self.uom_type == 'smaller':
            qty_reference = qty / self.factor
        elif self.uom_type == 'bigger':
            qty_reference = qty * self.factor
        else:
            qty_reference = qty
        
        # 2. Conversion vers l'unité de destination
        if to_uom.uom_type == 'smaller':
            return qty_reference * to_uom.factor
        elif to_uom.uom_type == 'bigger':
            return qty_reference / to_uom.factor
        else:
            return qty_reference
