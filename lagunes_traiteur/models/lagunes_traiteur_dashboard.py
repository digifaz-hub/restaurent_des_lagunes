# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import json
from datetime import datetime, timedelta

class LagunesTraiteurDashboard(models.TransientModel):
    _name = 'lagunes.traiteur.dashboard'
    _description = 'Tableau de Bord Traiteur'

    @api.model
    def get_dashboard_data(self):
        """Récupère toutes les stats pour le Dashboard Traiteur"""
        company_id = self.env.company.id
        today = datetime.now().date()
        month_start = today.replace(day=1)
        
        # 1. KPIs de base
        new_demands = self.env['lagunes.traiteur.demande'].search_count([
            ('company_id', '=', company_id), ('state', '=', 'new')
        ])
        
        ongoing_prestas = self.env['lagunes.traiteur.demande'].search_count([
            ('company_id', '=', company_id), 
            ('state', '=', 'accepte'), 
            ('date_fin', '>=', today)
        ])
        
        # CA Prévisionnel (Accepté ce mois-ci)
        confirmed_demands = self.env['lagunes.traiteur.demande'].search([
            ('company_id', '=', company_id), 
            ('state', '=', 'accepte'),
            ('date_debut', '>=', month_start)
        ])
        ca_mensuel = sum(confirmed_demands.mapped('montant_total_estime'))

        # KPIs Devis
        total_quotes = self.env['lagunes.traiteur.devis'].search_count([('company_id', '=', company_id)])
        sent_quotes = self.env['lagunes.traiteur.devis'].search_count([
            ('company_id', '=', company_id), ('state', '=', 'sent')
        ])
        accepted_quotes = self.env['lagunes.traiteur.devis'].search_count([
            ('company_id', '=', company_id), ('state', '=', 'accepted')
        ])
        refused_quotes = self.env['lagunes.traiteur.devis'].search_count([
            ('company_id', '=', company_id), ('state', '=', 'refused')
        ])
        revised_quotes = self.env['lagunes.traiteur.devis'].search_count([
            ('company_id', '=', company_id), ('state', '=', 'revised')
        ])
        
        # Taux de transformation (acceptés / (acceptés + refusés + révisés))
        processed_quotes = accepted_quotes + refused_quotes + revised_quotes
        ratio = (accepted_quotes / processed_quotes * 100) if processed_quotes > 0 else 0

        # 2. Prochaines Prestations (Timeline)
        upcoming = self.env['lagunes.traiteur.demande'].search([
            ('company_id', '=', company_id),
            ('state', '=', 'accepte'),
            ('date_debut', '>=', today)
        ], order='date_debut asc', limit=5)
        
        timeline = []
        for p in upcoming:
            timeline.append({
                'label': f"{p.main_type_prestation_id.name} — {p.nom_entreprise}",
                'sub': f"Du {p.date_debut} au {p.date_fin} ({p.total_nb_personnes} pers.)",
                'icon': p.main_type_prestation_id.icon or 'fa-calendar',
                'color': p.main_type_prestation_id.color or '#16166d',
            })


        # 3. Répartition par Type (Chart)
        types_stats = self.env['lagunes.traiteur.type.prestation'].search([])
        chart_data = {
            'labels': [t.name for t in types_stats],
            'datasets': [{
                'label': 'Nombre de demandes',
                'data': [self.env['lagunes.traiteur.demande'].search_count([
                    ('main_type_prestation_id', '=', t.id), ('company_id', '=', company_id)
                ]) for t in types_stats],

                'backgroundColor': [t.color or '#16166d' for t in types_stats],
            }]
        }

        # 4. Évolution du CA (6 derniers mois)
        revenue_labels = []
        revenue_values = []
        for i in range(5, -1, -1):
            d = today - timedelta(days=i*30)
            m_start = d.replace(day=1)
            # Calcul du CA accepté pour ce mois
            month_demands = self.env['lagunes.traiteur.demande'].search([
                ('company_id', '=', company_id),
                ('state', '=', 'accepte'),
                ('date_debut', '>=', m_start),
                ('date_debut', '<=', d) # Approximation simple pour le mois
            ])
            revenue_labels.append(m_start.strftime('%b'))
            revenue_values.append(sum(month_demands.mapped('montant_total_estime')))

        revenue_chart_data = {
            'labels': revenue_labels,
            'datasets': [{
                'label': 'CA Confirmé (FCFA)',
                'data': revenue_values,
                'backgroundColor': '#16166d',
                'borderRadius': 5,
            }]
        }

        # 5. Dernières Demandes (Table)
        recent_demands_recs = self.env['lagunes.traiteur.demande'].search([
            ('company_id', '=', company_id)
        ], order='create_date desc', limit=5)
        recent_demands = []
        for rd in recent_demands_recs:
            recent_demands.append({
                'id': rd.id,
                'reference': rd.reference,
                'entreprise': rd.nom_entreprise,
                'type': rd.main_type_prestation_id.name,
                'date': rd.date_debut,
                'state': rd.state,
                'state_label': dict(rd._fields['state'].selection).get(rd.state)
            })

        return {
            'kpis': {
                'new_demands': new_demands,
                'ongoing_prestas': ongoing_prestas,
                'ca_mensuel': f"{ca_mensuel:,.0f}".replace(',', ' '),
                'conversion_rate': round(ratio, 1),
                'sent_quotes': sent_quotes,
                'refused_quotes': refused_quotes,
                'revised_quotes': revised_quotes,
            },
            'timeline': timeline,
            'recent_demands': recent_demands,
            'chart_data': json.dumps(chart_data),
            'revenue_chart_data': json.dumps(revenue_chart_data),
        }

