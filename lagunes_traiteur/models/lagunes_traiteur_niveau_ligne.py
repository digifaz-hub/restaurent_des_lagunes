# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LagunesTraiteurNiveauLigne(models.Model):
    _name = 'lagunes.traiteur.niveau.ligne'
    _description = 'Ligne de Composition de Niveau'
    _order = 'sequence, id'
    _check_company_auto = True

    niveau_id = fields.Many2one('lagunes.traiteur.niveau', string='Niveau', required=True, ondelete='cascade')
    type_prestation_id = fields.Many2one('lagunes.traiteur.type.prestation', string='Type de prestation', help='Ligne spécifique à ce type de prestation')
    sequence = fields.Integer(string='Séquence', default=10)
    type_ligne = fields.Selection([
        ('plat', 'Plat de la cantine'),
        ('boisson', 'Boisson'),
        ('equipement', 'Équipement'),
        ('service', 'Service / Personnel'),
        ('autre', 'Autre')
    ], string='Type de contenu', required=True, default='plat')
    
    description = fields.Char(string='Description', required=True)
    quantite_par_personne = fields.Float(string='Qté par personne', default=1.0)
    unite = fields.Char(string='Unité', default='pièce')
    
    plat_type_id = fields.Many2one('lagunes.plat.type', string='Type de plat (Cantine)', ondelete='restrict', help='Pour lier aux types de plats existants')
    plat_id = fields.Many2one('lagunes.plat', string='Plat spécifique (Cantine)', ondelete='restrict', help='Si rempli, ce plat sera utilisé plutôt que le type de plat')
    is_client_choice = fields.Boolean(string='Au choix du client', default=False, help='Si coché, le client devra choisir ses plats dans le wizard')
    nb_choix = fields.Integer(string='Nb de choix possibles', default=1)
    
    logistique_id = fields.Many2one('lagunes.traiteur.logistique', string='Élément logistique')
