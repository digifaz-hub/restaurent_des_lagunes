# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LagunesTraiteurNiveau(models.Model):
    _name = 'lagunes.traiteur.niveau'
    _description = 'Niveau de Prestation Traiteur'
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char(string='Nom du niveau', required=True)
    type_prestation_ids = fields.Many2many(
        'lagunes.traiteur.type.prestation',
        'lagunes_traiteur_type_niveau_rel',
        'niveau_id',
        'type_id',
        string='Types de prestation',
    )
    sequence = fields.Integer(string='Séquence', default=10)
    description = fields.Text(string='Description des inclusions')
    
    prix_grid_ids = fields.One2many('lagunes.traiteur.niveau.prix', 'niveau_id', string='Grille tarifaire par type')

    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)

    active = fields.Boolean(default=True)
    is_recommended = fields.Boolean(string='Mettre en avant', default=False)
    
    ligne_ids = fields.One2many('lagunes.traiteur.niveau.ligne', 'niveau_id', string='Composition du menu')

    @api.onchange('type_prestation_ids')
    def _onchange_type_prestation_ids(self):
        """Synchronise automatiquement la grille tarifaire avec les types sélectionnés"""
        if not self.type_prestation_ids:
            self.prix_grid_ids = [(5, 0, 0)] # Vide tout si aucun type
            return

        current_types = self.prix_grid_ids.mapped('type_id')
        new_types = self.type_prestation_ids - current_types
        removed_types = current_types - self.type_prestation_ids

        commands = []
        # 1. Supprimer les types retirés
        for grid_line in self.prix_grid_ids:
            if grid_line.type_id in removed_types:
                commands.append((2, grid_line.id or grid_line._origin.id))

        # 2. Ajouter les nouveaux types
        for new_type in new_types:
            commands.append((0, 0, {
                'type_id': new_type.id,
                'prix_par_personne': 0.0,
            }))
        
        if commands:
            self.prix_grid_ids = commands
