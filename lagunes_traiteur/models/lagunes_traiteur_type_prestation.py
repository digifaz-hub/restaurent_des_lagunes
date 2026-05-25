# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LagunesTraiteurTypePrestation(models.Model):
    _name = 'lagunes.traiteur.type.prestation'
    _description = 'Type de Prestation Traiteur'
    _order = 'sequence, id'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code court', required=True)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    description = fields.Text(string='Description')
    icon = fields.Char(string='Icône FontAwesome', default='fa-cutlery')
    color = fields.Char(string='Couleur', default='#16166d')
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(default=True)
    image = fields.Image(string='Image illustrative')
    heure_service = fields.Char(string='Heure de service habituelle')
    duree_moyenne_heures = fields.Float(string='Durée moyenne (h)', default=2.0)
    
    niveau_ids = fields.Many2many(
        'lagunes.traiteur.niveau',
        'lagunes_traiteur_type_niveau_rel',
        'type_id',
        'niveau_id',
        string='Niveaux proposés',
    )

    DEFAULT_NIVEAUX = [
        ('Standard', 10),
        ('Renforcée', 20),
        ('Améliorée', 30),
        ('Complète', 40),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._attach_default_niveaux()
        return records

    def _attach_default_niveaux(self):
        Niveau = self.env['lagunes.traiteur.niveau']
        default_names = [name for name, _ in self.DEFAULT_NIVEAUX]
        generic_levels = Niveau.search([('name', 'in', default_names)])
        existing_names = generic_levels.mapped('name')
        for name, sequence in self.DEFAULT_NIVEAUX:
            if name not in existing_names:
                niveau = Niveau.create({
                    'name': name,
                    'sequence': sequence,
                    'description': f"Formule {name} générique.",
                })
                generic_levels |= niveau
        for record in self:
            to_add = [lvl.id for lvl in generic_levels if record.id not in lvl.type_prestation_ids.ids]
            if to_add:
                record.write({'niveau_ids': [(4, lvl_id) for lvl_id in to_add]})
