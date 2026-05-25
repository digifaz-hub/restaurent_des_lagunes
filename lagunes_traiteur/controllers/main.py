# -*- coding: utf-8 -*-
from odoo import http, _, fields
from odoo.http import request
from odoo.exceptions import UserError
import json
from datetime import timedelta, date
import urllib.parse

class LagunesTraiteurWeb(http.Controller):

    @http.route(['/traiteur'], type='http', auth="public", website=True)
    def traiteur_home(self, **post):
        """Page d'accueil du service traiteur"""
        company_id = request.website.company_id.id
        types = request.env['lagunes.traiteur.type.prestation'].sudo().search([
            ('active', '=', True),
            ('company_id', '=', company_id),
        ])
        config = request.env['lagunes.traiteur.config'].sudo().search(
            [('company_id', '=', company_id)], limit=1,
        )
        
        return request.render('lagunes_traiteur.website_traiteur_home', {
            'types': types,
            'config': config,
        })

    @http.route(['/traiteur/demande'], type='http', auth="public", website=True)
    def traiteur_wizard(self, **post):
        """Lancement du wizard multi-étapes"""
        company_id = request.website.company_id.id
        base_domain = [('active', '=', True), ('company_id', '=', company_id)]
        types = request.env['lagunes.traiteur.type.prestation'].sudo().search(base_domain)
        logistiques = request.env['lagunes.traiteur.logistique'].sudo().search(base_domain)
        niveaux = request.env['lagunes.traiteur.niveau'].sudo().search(base_domain)
        
        return request.render('lagunes_traiteur.website_traiteur_wizard', {
            'types': types,
            'logistiques': logistiques,
            'niveaux': niveaux,
        })

    @http.route(['/traiteur/demande/submit'], type='http', auth="public", website=True, methods=['POST'])
    def traiteur_submit(self, **post):
        """Réception du formulaire et création de la demande"""
        # 1. Extraction des données
        type_ids = request.httprequest.form.getlist('type_ids')
        selected_type_ids = [int(tid) for tid in type_ids if tid]

        # Extraction du niveau sélectionné
        niveau_id = post.get('niveau_id')
        selected_niveau_id = int(niveau_id) if niveau_id else False

        # Validation des dates
        from datetime import datetime
        date_mode = post.get('date_mode', 'range')  # 'single' ou 'range'
        date_debut_str = post.get('date_debut')
        date_fin_str = post.get('date_fin')
        
        if not date_debut_str:
            raise UserError(_("La date de début est obligatoire."))
        
        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        except ValueError:
            raise UserError(_("Format de date invalide."))
        
        # Mode 1 jour : date_fin = date_debut
        if date_mode == 'single':
            date_fin = date_debut
            date_fin_str = date_debut_str
        else:
            # Mode période : date_fin obligatoire
            if not date_fin_str:
                raise UserError(_("La date de fin est obligatoire pour une période."))
            try:
                date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
            except ValueError:
                raise UserError(_("Format de date invalide."))
        
        today = date.today()
        if date_debut < today:
            raise UserError(_("La date de début ne peut pas être dans le passé."))
        
        if date_fin < date_debut:
            raise UserError(_("La date de fin doit être postérieure ou égale à la date de début."))

        notes_client = post.get('notes') or ''
        menu_notes = post.get('menu_notes')
        if menu_notes:
            notes_client += '\n\nMenu: ' + menu_notes
        
        vals = {
            'nom_contact': post.get('nom'),
            'prenom_contact': post.get('prenom'),
            'email_contact': post.get('email'),
            'telephone_contact': post.get('phone'),
            'nom_entreprise': post.get('entreprise'),
            'adresse_prestation': post.get('adresse'),
            'notes_client': notes_client,
            'type_prestation_ids': [(6, 0, selected_type_ids)],
            'niveau_id': selected_niveau_id,
            'date_debut': date_debut_str,
            'date_fin': date_fin_str,
            'nb_personnes': int(post.get('nb_personnes', 1)),
            'company_id': request.website.company_id.id,
        }

        # 2. Création de la demande
        demande = request.env['lagunes.traiteur.demande'].sudo().create(vals)

        # 3. Traitement des options logistiques
        logistique_lines = []
        for key, value in post.items():
            if key.startswith('log_') and value and int(value) > 0:
                log_id = int(key.replace('log_', ''))
                logistique_lines.append((0, 0, {
                    'logistique_id': log_id,
                    'quantite': int(value),
                }))
        if logistique_lines:
            demande.logistique_line_ids = logistique_lines

        # 4. Création des jours de prestation (si dates fournies)
        if demande.date_debut and demande.date_fin:
            current_date = demande.date_debut
            while current_date <= demande.date_fin:
                request.env['lagunes.traiteur.demande.jour'].sudo().create({
                    'demande_id': demande.id,
                    'date': current_date,
                })
                current_date += timedelta(days=1)

        # 5. Envoi de l'email de confirmation automatique
        template = request.env.ref('lagunes_traiteur.email_template_confirmation_demande', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(demande.id, force_send=True)

        # 6. Redirection vers la confirmation
        return request.redirect(f'/traiteur/confirmation/{demande.reference.replace("/", "-")}')

    @http.route(['/traiteur/confirmation/<string:ref>'], type='http', auth="public", website=True)
    def traiteur_confirmation(self, ref, **post):
        """Page de succès après soumission"""
        company_id = request.website.company_id.id
        config = request.env['lagunes.traiteur.config'].sudo().search(
            [('company_id', '=', company_id)], limit=1,
        )
        return request.render('lagunes_traiteur.website_traiteur_confirmation', {
            'reference': ref.replace("-", "/"),
            'config': config,
        })
