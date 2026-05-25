# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LagunesTraiteurNiveauPrix(models.Model):
    _name = 'lagunes.traiteur.niveau.prix'
    _description = 'Grille Tarifaire Traiteur'
    _order = 'type_id, id'

    niveau_id = fields.Many2one('lagunes.traiteur.niveau', string='Niveau', required=True, ondelete='cascade')
    type_id = fields.Many2one('lagunes.traiteur.type.prestation', string='Type de Prestation', required=True)
    prix_par_personne = fields.Float(string='Prix par personne', required=True)
    
    currency_id = fields.Many2one('res.currency', string='Devise', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Société', related='niveau_id.company_id', store=True)

    _sql_constraints = [
        ('type_niveau_unique', 'unique(niveau_id, type_id)', 'Il existe déjà un prix pour ce type de prestation sur ce niveau !')
    ]
