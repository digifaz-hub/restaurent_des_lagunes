# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class LagunesTraiteurDemandePrestation(models.Model):
    _name = 'lagunes.traiteur.demande.prestation'
    _description = 'Prestation spécifique par jour'
    _order = 'heure_prestation, id'
    _check_company_auto = True

    jour_id = fields.Many2one('lagunes.traiteur.demande.jour', string='Jour de prestation', required=True, ondelete='cascade')
    demande_id = fields.Many2one('lagunes.traiteur.demande', related='jour_id.demande_id', store=True, readonly=True)
    
    type_prestation_id = fields.Many2one('lagunes.traiteur.type.prestation', string='Type de prestation', required=True)
    niveau_id = fields.Many2one('lagunes.traiteur.niveau', string='Niveau / Formule', required=True)
    
    heure_prestation = fields.Float(string='Heure de prestation', default=12.0)
    nb_personnes = fields.Integer(string='Nombre de personnes', default=1)
    nb_jours = fields.Integer(string='Nombre de jours', compute='_compute_nb_jours', store=True)
    prix_unitaire = fields.Float(string='Prix unitaire / Pers', default=0.0)
    
    plat_line_ids = fields.One2many('lagunes.traiteur.demande.plat', 'prestation_id', string='Plats et Options')
    
    montant_total = fields.Monetary(string='Montant Total', compute='_compute_montant_total', currency_field='currency_id', store=True)
    currency_id = fields.Many2one('res.currency', related='demande_id.currency_id')
    @api.depends('nb_personnes', 'nb_jours', 'prix_unitaire', 'plat_line_ids.prix_unitaire', 'plat_line_ids.quantite')
    def _compute_montant_total(self):
        for rec in self:
            # 1. Calcul du forfait groupe (si prix_unitaire défini dans la grille)
            total = rec.nb_personnes * rec.nb_jours * rec.prix_unitaire
            
            # 2. Ajout des plats individuels (extras ou si pas de forfait global)
            for line in rec.plat_line_ids:
                total += line.quantite * rec.nb_jours * line.prix_unitaire
                
            rec.montant_total = total

    @api.onchange('niveau_id', 'type_prestation_id', 'nb_personnes')
    def _onchange_niveau_id(self):
        """Action groupée : Calcul du prix grille + Génération automatique des plats"""
        if not self.niveau_id:
            return

        # 1. Recherche du prix spécifique dans la grille
        if self.type_prestation_id:
            grid_price = self.niveau_id.prix_grid_ids.filtered(lambda p: p.type_id == self.type_prestation_id)
            if grid_price:
                self.prix_unitaire = grid_price[0].prix_par_personne
            else:
                self.prix_unitaire = 0.0

        # 2. Initialisation des plats en fonction du niveau
        if self.nb_personnes:
            new_lines = []
            lignes = self.niveau_id.ligne_ids.filtered(
                lambda l: not l.type_prestation_id or l.type_prestation_id == self.type_prestation_id
            )
            for ligne in lignes:
                if not ligne.is_client_choice:
                    vals = {
                        'description': ligne.description,
                        'quantite': ligne.quantite_par_personne * self.nb_personnes,
                        'niveau_ligne_id': ligne.id,
                    }
                    if ligne.type_ligne == 'plat':
                        if ligne.plat_id:
                            vals.update({
                                'plat_id': ligne.plat_id.id,
                                'description': ligne.plat_id.name,
                                'prix_unitaire': 0.0 if self.prix_unitaire > 0 else ligne.plat_id.prix_unitaire,
                            })
                        elif ligne.plat_type_id:
                            plat = self.env['lagunes.plat'].search([('plat_type_id', '=', ligne.plat_type_id.id)], limit=1)
                            if plat:
                                vals.update({
                                    'plat_id': plat.id,
                                    'description': plat.name,
                                    'prix_unitaire': 0.0 if self.prix_unitaire > 0 else plat.prix_unitaire,
                                })
                    elif ligne.type_ligne == 'equipement' and ligne.logistique_id:
                        vals['logistique_id'] = ligne.logistique_id.id
                        vals['prix_unitaire'] = 0.0 if self.prix_unitaire > 0 else ligne.logistique_id.prix_unitaire
                    
                    new_lines.append((0, 0, vals))
            self.plat_line_ids = new_lines

    @api.onchange('type_prestation_id')
    def _onchange_type_prestation(self):
        if self.type_prestation_id:
            # Suggérer l'heure par défaut du type
            if self.type_prestation_id.heure_service:
                try:
                    h, m = self.type_prestation_id.heure_service.lower().replace('h', ':').split(':')
                    self.heure_prestation = float(h) + float(m)/60
                except (ValueError, AttributeError):
                    pass
            
            # Filtrer les niveaux liés à ce type
            return {'domain': {'niveau_id': [
                ('type_prestation_ids', 'in', self.type_prestation_id.id)
            ]}}

    @api.depends('demande_id.date_debut', 'demande_id.date_fin')
    def _compute_nb_jours(self):
        for rec in self:
            if rec.demande_id.date_debut and rec.demande_id.date_fin:
                delta = rec.demande_id.date_fin - rec.demande_id.date_debut
                rec.nb_jours = delta.days + 1
            else:
                rec.nb_jours = 1

    def _compute_display_name(self):
        for rec in self:
            h = int(rec.heure_prestation)
            m = int(60 * (rec.heure_prestation - h))
            rec.display_name = f"{rec.type_prestation_id.name} (%02dh%02d)" % (h, m)

