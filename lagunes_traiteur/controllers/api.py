# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from datetime import datetime, timedelta

class LagunesTraiteurApi(http.Controller):

    @http.route(['/traiteur/api/niveaux'], type='json', auth="public", website=True)
    def get_niveaux(self, type_id, **post):
        """Retourne les niveaux disponibles pour un type de prestation donné"""
        company_id = request.website.company_id.id
        niveaux = request.env['lagunes.traiteur.niveau'].sudo().search([
            ('type_prestation_ids', 'in', int(type_id)),
            ('active', '=', True),
            ('company_id', '=', company_id),
        ])
        return [{
            'id': n.id,
            'name': n.name,
            'price': n.prix_par_personne,
            'description': n.description,
            'is_recommended': n.is_recommended,
        } for n in niveaux]

    @http.route(['/traiteur/api/estimation'], type='json', auth="public", website=True)
    def get_estimation(self, niveau_id, nb_personnes, nb_jours, logistique=None, **post):
        """Calcule l'estimation tarifaire en temps réel"""
        company_id = request.website.company_id.id
        niveau = request.env['lagunes.traiteur.niveau'].sudo().browse(int(niveau_id))
        # Sécurité multi-société : le niveau doit appartenir à la société
        # du site courant, sinon on refuse la requête (on ne révèle aucun prix).
        if not niveau.exists() or niveau.company_id.id != company_id:
            return {'total': 0}

        montant_base = niveau.prix_par_personne * int(nb_personnes) * int(nb_jours)

        montant_logistique = 0
        if logistique:
            for log_id, qty in logistique.items():
                log_obj = request.env['lagunes.traiteur.logistique'].sudo().browse(int(log_id))
                if log_obj.exists() and log_obj.company_id.id == company_id:
                    montant_logistique += log_obj.prix_unitaire * int(qty)

        return {
            'montant_base': montant_base,
            'montant_logistique': montant_logistique,
            'total': montant_base + montant_logistique
        }

    @http.route(['/traiteur/api/menus_disponibles'], type='json', auth="public", website=True)
    def get_menus_disponibles(self, date_debut, date_fin, **post):
        """Retourne les plats disponibles pour chaque jour de la période"""
        d_start = datetime.strptime(date_debut, '%Y-%m-%d').date()
        d_end = datetime.strptime(date_fin, '%Y-%m-%d').date()
        
        config = request.env['lagunes.traiteur.config'].sudo().search([
            ('company_id', '=', request.website.company_id.id)
        ], limit=1)
        
        jours_avance = config.jours_avance_menu or 3
        date_limite = datetime.now().date() + timedelta(days=jours_avance)
        
        result = []
        curr = d_start
        while curr <= d_end:
            jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
            day_data = {
                'date': curr.strftime('%Y-%m-%d'),
                'label': jours_fr[curr.weekday()] + ' ' + curr.strftime('%d/%m'),
                'disponible': curr <= date_limite,
                'plats_par_type': {}
            }
            
            if day_data['disponible']:
                # Calcul du samedi de la semaine (début de semaine cantine).
                days_since_sat = (curr.weekday() - 5) % 7
                week_start = curr - timedelta(days=days_since_sat)

                menu = request.env['lagunes.week.menu'].sudo().search([
                    ('week_start_date', '=', week_start),
                    ('state', '=', 'published'),
                    ('active', '=', True),
                    ('company_id', '=', request.website.company_id.id),
                ], limit=1)

                if menu:
                    # Mapping Python weekday() (Lun=0…Dim=6) vers le code
                    # `day` du modèle lagunes.week.menu.line (Sam='0'…Ven='6').
                    day_code = str((curr.weekday() + 2) % 7)

                    lines = menu.menu_line_ids.filtered(
                        lambda l: l.day == day_code
                    )
                    for line in lines:
                        t_name = line.plat_type_id.name or 'Plat'
                        day_data['plats_par_type'].setdefault(t_name, [])
                        for plat in line.plat_ids:
                            day_data['plats_par_type'][t_name].append({
                                'id': plat.id,
                                'name': plat.display_name_website or plat.name,
                                'image': bool(plat.image_1920),
                            })
            
            result.append(day_data)
            curr += timedelta(days=1)
            
        return result
