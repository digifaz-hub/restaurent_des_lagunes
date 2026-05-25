# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class LagunesPortal(CustomerPortal):
    """
    Extension du portail client pour afficher les commandes cantine
    (optionnel - pour les clients ayant un compte Odoo)
    """
    
    def _prepare_home_portal_values(self, counters):
        """Ajouter le compteur de commandes cantine"""
        values = super()._prepare_home_portal_values(counters)
        
        if 'commande_count' in counters:
            partner = request.env.user.partner_id
            if partner.is_cantine_client:
                commande_count = request.env['lagunes.commande'].search_count([
                    ('company_id', '=', request.env.company.id),
                    ('entreprise_id', '=', partner.commercial_partner_id.id)
                ])
                values['commande_count'] = commande_count
        
        return values
    
    @http.route(['/my/commandes', '/my/commandes/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_my_commandes(self, page=1, date_begin=None, date_end=None, 
                            sortby=None, filterby=None, **kwargs):
        """Page portail pour voir les commandes cantine"""
        partner = request.env.user.partner_id
        
        if not partner.is_cantine_client:
            return request.redirect('/my')
        
        domain = [
            ('company_id', '=', request.env.company.id),
            ('entreprise_id', '=', partner.commercial_partner_id.id)
        ]
        
        # Filtres par date
        if date_begin and date_end:
            domain += [('date', '>=', date_begin), ('date', '<=', date_end)]
        
        # Tri
        searchbar_sortings = {
            'date': {'label': 'Date', 'order': 'date desc'},
            'reference': {'label': 'Référence', 'order': 'reference'},
            'state': {'label': 'Statut', 'order': 'state'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Pagination
        commandes = request.env['lagunes.commande'].search(domain, order=order)
        
        return request.render('lagunes_cantine.portal_my_commandes', {
            'commandes': commandes,
            'page_name': 'commande',
            'default_url': '/my/commandes',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
