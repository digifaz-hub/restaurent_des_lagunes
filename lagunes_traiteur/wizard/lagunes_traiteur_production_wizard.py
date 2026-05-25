# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date

class LagunesTraiteurProductionWizard(models.TransientModel):
    _name = 'lagunes.traiteur.production.wizard'
    _description = 'Assistant Fiche de Production'

    date_production = fields.Date(string='Date de production', default=fields.Date.today, required=True)
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)

    def action_generate_report(self):
        """Lance l'impression du rapport consolidé"""
        self.ensure_one()
        return self.env.ref('lagunes_traiteur.action_report_traiteur_production_consolidated').report_action(self)

    def get_production_data(self):
        """Calcule les données agrégées pour le rapport"""
        self.ensure_one()
        # 1. Trouver tous les jours de prestation à cette date
        jours = self.env['lagunes.traiteur.demande.jour'].search([
            ('date', '=', self.date_production),
            ('demande_id.state', 'in', ['en_cours', 'devis_envoye', 'accepte']),
            ('demande_id.company_id', '=', self.company_id.id)
        ])

        ingredients_map = {} # { (article_id, unit_id): { 'qty': X, 'name': Y, 'unit': Z, 'events': [ref1, ref2] } }
        plats_list = []

        for jour in jours:
            demande = jour.demande_id
            for plat_line in jour.plat_line_ids:
                plat = plat_line.plat_id
                plats_list.append({
                    'plat': plat.name,
                    'event': f"{demande.reference} ({demande.nom_entreprise or demande.nom_contact})",
                    'qty': demande.nb_personnes
                })

                if hasattr(plat, 'ingredient_ids'):
                    for ing in plat.ingredient_ids:
                        if not ing.market_article_id: continue
                        
                        key = (ing.market_article_id.id, ing.uom_id.id)
                        total_qty = ing.quantite * demande.nb_personnes
                        
                        if key not in ingredients_map:
                            ingredients_map[key] = {
                                'name': ing.market_article_id.name,
                                'qty': 0.0,
                                'unit': ing.uom_id.name,
                                'events': set()
                            }
                        
                        ingredients_map[key]['qty'] += total_qty
                        ingredients_map[key]['events'].add(demande.reference)

        # Transformer en liste triée par nom
        ingredients_list = sorted(ingredients_map.values(), key=lambda x: x['name'])
        
        return {
            'date': self.date_production,
            'ingredients': ingredients_list,
            'plats_details': plats_list,
        }
