# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LagunesTraiteurLogistiqueLine(models.Model):
    _name = 'lagunes.traiteur.logistique.line'
    _description = 'Ligne Logistique de Demande'
    _check_company_auto = True

    demande_id = fields.Many2one('lagunes.traiteur.demande', string='Demande', required=True, ondelete='cascade')
    logistique_id = fields.Many2one('lagunes.traiteur.logistique', string='Élément', required=True)
    description = fields.Char(string='Description', related='logistique_id.name', readonly=True)
    quantite = fields.Integer(string='Quantité', default=1)
    prix_unitaire = fields.Float(string='Prix unitaire', related='logistique_id.prix_unitaire', readonly=True)
    sous_total = fields.Float(string='Sous-total', compute='_compute_sous_total', store=True)

    @api.depends('quantite', 'prix_unitaire')
    def _compute_sous_total(self):
        for line in self:
            line.sous_total = line.quantite * line.prix_unitaire
