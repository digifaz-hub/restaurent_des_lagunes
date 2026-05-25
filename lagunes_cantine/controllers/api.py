# -*- coding: utf-8 -*-
# Nouveau fichier : controllers/api.py
# Routes JSON pour le frontend du menu hebdomadaire

from odoo import http
from odoo.http import request


class LagunesCantineApi(http.Controller):
    """API JSON interne pour le portail web cantine"""

    @http.route('/cantine/api/plats-du-jour', type='json', auth='public', website=True, csrf=False)
    def plats_du_jour(self, entreprise_id=None, week_menu_id=None,
                      day=None, plat_type_id=None, **kwargs):
        """
        Retourne les plats disponibles pour un jour et un type de plat donnés,
        depuis le menu hebdomadaire.
        """
        if not week_menu_id or day is None or not plat_type_id:
            return {'plats': [], 'notes_day': '', 'type_slug': 'resistance'}

        week_menu = request.env['lagunes.week.menu'].sudo().browse(int(week_menu_id))
        if not week_menu.exists():
            return {'plats': [], 'notes_day': '', 'type_slug': 'resistance'}

        # Trouver la ligne correspondante
        lines = week_menu.menu_line_ids.filtered(
            lambda l: l.day == str(day) and l.plat_type_id.id == int(plat_type_id)
        )

        plats_data = []
        notes_day = ''
        type_slug = 'resistance'

        for line in lines:
            if line.notes_day:
                notes_day = line.notes_day

            # Déterminer le slug du type
            type_name = line.plat_type_id.name.lower()
            if 'entr' in type_name:
                type_slug = 'entree'
            elif 'dessert' in type_name:
                type_slug = 'dessert'
            else:
                type_slug = 'resistance'

            for plat in line.plat_ids:
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                plats_data.append({
                    'id': plat.id,
                    'name': plat.name,
                    'description': plat.description or '',
                    'category': plat.category_id.name if plat.category_id else '',
                    'image': f'/web/image/lagunes.plat/{plat.id}/image_128' if plat.image_128 else '',
                })

        return {
            'plats': plats_data,
            'notes_day': notes_day,
            'type_slug': type_slug,
        }

    @http.route('/cantine/api/options', type='json', auth='public', website=True, csrf=False)
    def get_options(self, entreprise_id=None, **kwargs):
        """Retourne les options globales disponibles"""
        options = request.env['lagunes.plat.option'].sudo().search([
            ('active', '=', True),
            ('is_global', '=', True),
        ], order='sequence')
        return {
            'options': [{'id': o.id, 'name': o.name} for o in options]
        }