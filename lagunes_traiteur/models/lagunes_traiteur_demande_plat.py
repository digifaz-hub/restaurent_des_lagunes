# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LagunesTraiteurDemandePlat(models.Model):
    _name = 'lagunes.traiteur.demande.plat'
    _description = 'Plat sélectionné pour Prestation'
    _check_company_auto = True

    prestation_id = fields.Many2one('lagunes.traiteur.demande.prestation', string='Prestation', required=True, ondelete='cascade')
    demande_id = fields.Many2one('lagunes.traiteur.demande', related='prestation_id.demande_id', store=True, readonly=True)
    
    description = fields.Char(string='Désignation', required=True)
    plat_id = fields.Many2one('lagunes.plat', string='Plat (Cantine)')
    accompagnement_id = fields.Many2one('product.product', string='Accompagnement', domain=[('type', '=', 'consu')])
    logistique_id = fields.Many2one('lagunes.traiteur.logistique', string='Équipement (Logistique)')
    
    plat_type_id = fields.Many2one('lagunes.plat.type', string='Type de plat', related='plat_id.plat_type_id', store=True)
    
    quantite = fields.Float(string='Quantité', default=1.0)
    prix_unitaire = fields.Monetary(string='Prix unitaire', currency_field='currency_id')
    sous_total = fields.Monetary(string='Sous-total', compute='_compute_sous_total', currency_field='currency_id', store=True)
    
    currency_id = fields.Many2one('res.currency', related='demande_id.currency_id')
    niveau_ligne_id = fields.Many2one('lagunes.traiteur.niveau.ligne', string='Inclus dans la formule')
    notes = fields.Text(string='Notes spéciales')

    @api.depends('quantite', 'prix_unitaire')
    def _compute_sous_total(self):
        for rec in self:
            rec.sous_total = rec.quantite * rec.prix_unitaire

    @api.onchange('plat_id')
    def _onchange_plat_id(self):
        if self.plat_id:
            self.description = self.plat_id.name
            self.prix_unitaire = self.plat_id.prix_unitaire
            if self.plat_id.is_plat_resistance and self.plat_id.accompagnement_product_id:
                self.accompagnement_id = self.plat_id.accompagnement_product_id.id

    @api.onchange('logistique_id')
    def _onchange_logistique_id(self):
        if self.logistique_id:
            self.description = self.logistique_id.name
            self.prix_unitaire = self.logistique_id.prix_unitaire

