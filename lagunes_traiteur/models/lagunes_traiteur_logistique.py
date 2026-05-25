# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LagunesTraiteurLogistique(models.Model):
    _name = 'lagunes.traiteur.logistique'
    _description = 'Équipement Logistique Traiteur'
    _order = 'sequence, id'

    name = fields.Char(string='Nom de l\'élément', required=True)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    prix_unitaire = fields.Float(string='Prix unitaire', default=0.0)
    unite = fields.Char(string='Unité de facturation', default='par unité')
    description = fields.Text(string='Description pour le portail')
    icon = fields.Char(string='Icône FontAwesome', default='fa-cube')
    product_id = fields.Many2one('product.product', string='Produit Odoo lié', help='Pour la facturation automatique')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(string='Séquence', default=10)
    is_default_included = fields.Boolean(string='Inclus par défaut', default=False)
