# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LagunesTraiteurPropositionLine(models.Model):
    _name = 'lagunes.traiteur.proposition.line'
    _description = 'Ligne de Proposition de Menu'
    _order = 'jour_id, plat_type_sequence, sequence, id'

    proposition_id = fields.Many2one(
        'lagunes.traiteur.proposition',
        string='Proposition',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='proposition_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='proposition_id.currency_id', readonly=True)

    sequence = fields.Integer(string='Séquence', default=10)

    jour_id = fields.Many2one(
        'lagunes.traiteur.demande.jour',
        string='Jour',
        domain="[('demande_id', '=', parent.demande_id)]",
        help="Jour de prestation auquel cet élément est rattaché (optionnel).",
    )

    plat_type_id = fields.Many2one(
        'lagunes.plat.type',
        string='Catégorie',
        required=False,
        ondelete='restrict',
        help="Entrée, Plat de résistance, Dessert. Laisser vide pour les boissons (produits)."
    )
    plat_type_sequence = fields.Integer(
        related='plat_type_id.sequence',
        store=True,
        readonly=True,
    )

    plat_id = fields.Many2one(
        'lagunes.plat',
        string='Plat (catalogue cantine)',
        domain="[('plat_type_id', '=', plat_type_id), ('active', '=', True)]",
        ondelete='restrict',
    )
    accompagnement_id = fields.Many2one(
        'product.product',
        string='Accompagnement',
        domain=[('type', '=', 'consu')],
        ondelete='restrict',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Produit (boisson)',
        domain=[('product_tag_ids.name', 'ilike', 'Boisson')],
        ondelete='restrict',
        help="Pour les boissons : sélectionner un produit taggué 'Boisson'.",
    )
    logistique_id = fields.Many2one(
        'lagunes.traiteur.logistique',
        string='Élément logistique',
        ondelete='restrict',
        help="Pour les équipements issus du catalogue logistique.",
    )
    # Pour le regroupement dans le PDF (repas complet vs collation)
    prestation_id = fields.Many2one(
        'lagunes.traiteur.demande.prestation',
        string='Prestation liée',
        ondelete='set null',
        help="Permet de regrouper les lignes par type de prestation dans le PDF.",
    )

    description = fields.Char(
        string='Désignation',
        required=True,
        help="Texte affiché dans la proposition (toujours modifiable).",
    )
    quantite = fields.Float(string='Quantité', default=1.0)
    unite = fields.Char(string='Unité', default='pièce')
    prix_unitaire = fields.Monetary(string='Prix unitaire', currency_field='currency_id')
    sous_total = fields.Monetary(
        string='Sous-total',
        compute='_compute_sous_total',
        currency_field='currency_id',
        store=True,
    )
    notes = fields.Char(string='Notes')

    @api.depends('quantite', 'prix_unitaire')
    def _compute_sous_total(self):
        for rec in self:
            rec.sous_total = (rec.quantite or 0.0) * (rec.prix_unitaire or 0.0)

    @api.onchange('plat_id')
    def _onchange_plat_id(self):
        if self.plat_id:
            self.description = self.plat_id.name
            self.prix_unitaire = self.plat_id.prix_unitaire
            if self.plat_id.plat_type_id and not self.plat_type_id:
                self.plat_type_id = self.plat_id.plat_type_id
            if self.plat_id.is_plat_resistance and self.plat_id.accompagnement_product_id:
                self.accompagnement_id = self.plat_id.accompagnement_product_id.id
            self.product_id = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.prix_unitaire = self.product_id.list_price
            self.plat_id = False
            self.plat_type_id = False

    @api.onchange('logistique_id')
    def _onchange_logistique_id(self):
        if self.logistique_id:
            self.description = self.logistique_id.name
            self.prix_unitaire = self.logistique_id.prix_unitaire
            if self.logistique_id.unite:
                self.unite = self.logistique_id.unite
            self.plat_id = False
            self.product_id = False

    @api.onchange('plat_type_id')
    def _onchange_plat_type_id(self):
        # Réinitialiser le plat sélectionné si la catégorie change pour éviter les incohérences.
        if self.plat_id and self.plat_type_id and self.plat_id.plat_type_id != self.plat_type_id:
            self.plat_id = False
