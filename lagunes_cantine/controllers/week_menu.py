# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from datetime import date, datetime, timedelta


class LagunesWeekMenuController(http.Controller):

    # ================================================================== #
    #  MENU HEBDOMADAIRE                                                   #
    # ================================================================== #

    @http.route('/cantine/menu', type='http', auth='public', website=True)
    def week_menu_display(self, **kwargs):
        entreprise_id = request.session.get('cantine_entreprise_id')
        if not entreprise_id:
            return request.redirect('/cantine')

        entreprise = request.env['res.partner'].sudo().browse(entreprise_id)
        if not entreprise.exists():
            request.session.clear()
            return request.redirect('/cantine')

        today = date.today()
        days_since_saturday = (today.weekday() - 5) % 7
        week_start = today - timedelta(days=days_since_saturday)

        current_company_id = request.website.company_id.id
        week_menu = request.env['lagunes.week.menu'].sudo().search([
            ('company_id', '=', current_company_id),
            '|',
            ('is_global', '=', True),
            ('partner_id', '=', entreprise_id),
            ('week_start_date', '=', week_start),
            ('state', '=', 'published'),
            ('active', '=', True),
        ], limit=1)

        if not week_menu:
            # Fallback : on autorise uniquement un menu dont la semaine n'est
            # PAS encore terminée (menu de la semaine courante manquant mais
            # un menu futur peut exister). On ne retombe JAMAIS sur un menu
            # passé — ce serait trompeur pour le client.
            week_menu = request.env['lagunes.week.menu'].sudo().search([
                ('company_id', '=', current_company_id),
                '|',
                ('is_global', '=', True),
                ('partner_id', '=', entreprise_id),
                ('state', '=', 'published'),
                ('active', '=', True),
                ('week_end_date', '>=', today),
            ], order='week_start_date asc', limit=1)

        rules = request.env['lagunes.partner.plat.type.rule'].sudo().search([
            ('partner_id', '=', entreprise_id),
        ])

        if rules:
            visible_type_ids = [r.plat_type_id.id for r in rules if r.is_proposed]
        else:
            all_types = request.env['lagunes.plat.type'].sudo().search([('active', '=', True)])
            visible_type_ids = all_types.ids

        employe_id = request.session.get('cantine_employe_id')
        employe_name = request.session.get('cantine_employe_name', '')
        if employe_id:
            employe = request.env['lagunes.employe'].sudo().browse(employe_id)
            if employe.exists() and employe.plat_type_ids:
                visible_type_ids = list(set(visible_type_ids) & set(employe.plat_type_ids.ids))

        plat_types = request.env['lagunes.plat.type'].sudo().search(
            [('active', '=', True), ('id', 'in', visible_type_ids)],
            order='sequence'
        )

        if entreprise.menu_category_ids:
            accessible_category_ids = entreprise.menu_category_ids.ids
        else:
            all_cats = request.env['lagunes.menu.category'].sudo().search([('active', '=', True)])
            accessible_category_ids = all_cats.ids

        if employe_id:
            employe = request.env['lagunes.employe'].sudo().browse(employe_id)
            if employe.exists() and employe.menu_category_ids:
                accessible_category_ids = list(set(accessible_category_ids) & set(employe.menu_category_ids.ids))

        hors_menu_plats = request.env['lagunes.plat'].sudo().search([
            ('company_id', '=', current_company_id),
            ('is_global_available', '=', True),
            ('active', '=', True),
            ('plat_type_id', 'in', visible_type_ids),
        ])

        hors_menu_by_type = {}
        for pt in plat_types:
            plats = hors_menu_plats.filtered(lambda p: p.plat_type_id.id == pt.id)
            if plats:
                hors_menu_by_type[pt] = plats

        heure_limite_atteinte, heure_limite_display = False, ''
        allowed, hl = entreprise.is_commande_allowed_now()
        if not allowed:
            heure_limite_atteinte = True
            heure_limite_display = hl or ''

        # ── Limite session : prendre en compte max_commandes_par_jour de l'employé
        max_session = 1
        commandes_aujourd_hui = 0
        # Nouvelles variables pour la logique "commander pour autres"
        peut_commander_pour_autres = False
        nb_personnes_autorisees = 0

        if employe_id:
            employe = request.env['lagunes.employe'].sudo().browse(employe_id)
            if employe.exists():
                max_session = max(1, employe.max_commandes_par_jour or 1)
                commandes_aujourd_hui = request.env['lagunes.commande'].sudo().search_count([
                    ('company_id', '=', current_company_id),
                    ('entreprise_id', '=', entreprise_id),
                    ('date', '=', today),
                    ('employee_name', '=', employe.display_name_full),
                    ('state', '!=', 'cancelled'),
                ])
                # Nouvelles données pour le template
                peut_commander_pour_autres = employe.peut_commander_pour_autres
                nb_personnes_autorisees = employe.nb_personnes_autorisees if employe.peut_commander_pour_autres else 0
        else:
            max_session = entreprise.max_orders_per_session or 1
            commandes_aujourd_hui = request.session.get('cantine_session_order_count', 0)

        limit_reached_session = (commandes_aujourd_hui >= max_session)

        menu_by_day_type = {}
        if week_menu:
            for line in week_menu.menu_line_ids:
                if line.menu_category_id and line.menu_category_id.id not in accessible_category_ids:
                    continue
                day_int = int(line.day)
                if day_int not in menu_by_day_type:
                    menu_by_day_type[day_int] = {}
                if line.plat_type_id.id not in menu_by_day_type[day_int]:
                    menu_by_day_type[day_int][line.plat_type_id.id] = []
                menu_by_day_type[day_int][line.plat_type_id.id].append(line)

        jours_labels = {
            0: 'Samedi', 1: 'Dimanche', 2: 'Lundi',
            3: 'Mardi', 4: 'Mercredi', 5: 'Jeudi', 6: 'Vendredi'
        }

        jours_dates = {}
        if week_menu and week_menu.week_start_date:
            for i in range(7):
                jours_dates[i] = week_menu.week_start_date + timedelta(days=i)

        values = {
            'week_menu': week_menu,
            'plat_types': plat_types,
            'entreprise': entreprise,
            'employe_name': employe_name,
            'employe_id': employe_id,
            'menu_by_day_type': menu_by_day_type,
            'jours_labels': jours_labels,
            'jours_dates': jours_dates,
            'hors_menu_plats': hors_menu_plats,
            'hors_menu_by_type': hors_menu_by_type,
            'accessible_category_ids': accessible_category_ids,
            'heure_limite_atteinte': heure_limite_atteinte,
            'heure_limite_display': heure_limite_display,
            'limit_reached_session': limit_reached_session,
            'today': today,
            'today_day_idx': (today.weekday() - 5) % 7,
            # Info sur les commandes déjà passées
            'commandes_aujourd_hui': commandes_aujourd_hui,
            'max_commandes_employe': max_session,
            # NOUVEAU : logique "commander pour autres"
            'peut_commander_pour_autres': peut_commander_pour_autres,
            'nb_personnes_autorisees': nb_personnes_autorisees,
        }

        return request.render('lagunes_cantine.week_menu_table', values)

    @http.route('/cantine/api/plats-du-jour', type='json', auth='public', website=True, csrf=False)
    def api_get_plats_du_jour(self, entreprise_id, week_menu_id, day, plat_type_id, **kwargs):
        if not entreprise_id:
            return {'plats': [], 'type_slug': 'resistance'}

        entreprise = request.env['res.partner'].sudo().browse(int(entreprise_id))
        if not entreprise.exists():
            return {'plats': [], 'type_slug': 'resistance'}

        plat_type = request.env['lagunes.plat.type'].sudo().browse(int(plat_type_id))
        slug = 'resistance'
        pt_name = plat_type.name.lower()
        if 'entr' in pt_name: slug = 'entree'
        elif 'dessert' in pt_name: slug = 'dessert'

        lines = request.env['lagunes.week.menu.line'].sudo().search([
            ('week_menu_id', '=', int(week_menu_id) if week_menu_id else False),
            ('week_menu_id.company_id', '=', request.website.company_id.id),
            ('day', '=', str(day)),
            ('plat_type_id', '=', int(plat_type_id)),
        ])

        allowed_cat_ids = entreprise.menu_category_ids.ids if entreprise.menu_category_ids else []
        if not allowed_cat_ids:
            allowed_cat_ids = request.env['lagunes.menu.category'].sudo().search([('active', '=', True)]).ids

        employe_id = request.session.get('cantine_employe_id')
        if employe_id:
            employe = request.env['lagunes.employe'].sudo().browse(employe_id)
            if employe.exists() and employe.menu_category_ids:
                allowed_cat_ids = list(set(allowed_cat_ids) & set(employe.menu_category_ids.ids))

        if allowed_cat_ids:
            lines = lines.filtered(lambda l: l.menu_category_id.id in allowed_cat_ids)
        else:
            lines = request.env['lagunes.week.menu.line'].sudo().browse()

        plats_data = []
        notes_day = ""
        for line in lines:
            if line.notes_day:
                notes_day = line.notes_day
            for plat in line.plat_ids:
                plats_data.append({
                    'id': plat.id,
                    'name': plat.name,
                    'image': f'/web/image/lagunes.plat/{plat.id}/image_128' if plat.image_128 else False,
                    'category': line.menu_category_id.name if line.menu_category_id else False,
                })

        return {
            'plats': plats_data,
            'type_slug': slug,
            'notes_day': notes_day,
        }

    # ================================================================== #
    #  COMMANDER DEPUIS LE MENU HEBDO                                     #
    # ================================================================== #

    @http.route('/cantine/commander-semaine', type='json', auth='public', website=True, csrf=False)
    def commander_depuis_semaine(self, entreprise_id, week_menu_id, day,
                                  plats_choisis=None, option_ids=None, notes='',
                                  order_for_other=False, ordered_for_name='', **kwargs):
        """
        Passer une commande depuis le menu hebdomadaire.
        plats_choisis : dict {slug: plat_id}  (entree / resistance / dessert)
        """
        if not request.session.get('cantine_entreprise_id'):
            return {'success': False, 'message': 'Session expirée. Veuillez vous reconnecter.'}

        session_id = request.session.get('cantine_entreprise_id')
        if not session_id or int(session_id) != int(entreprise_id):
            return {'success': False, 'message': 'Accès non autorisé.'}

        entreprise = request.env['res.partner'].sudo().browse(entreprise_id)

        # Vérifier heure limite
        allowed, heure_limite = entreprise.is_commande_allowed_now()
        if not allowed:
            return {'success': False, 'message': f'Les commandes sont closes depuis {heure_limite}.'}

        # Vérifier que le jour correspond à aujourd'hui
        today = date.today()
        today_day_idx = (today.weekday() - 5) % 7
        if int(day) != today_day_idx:
            return {'success': False, 'message': "Désolé, vous ne pouvez passer commande que pour aujourd'hui."}

        employe_id = request.session.get('cantine_employe_id')
        employe_name = request.session.get('cantine_employe_name', '')
        employe = None

        # ── Récupérer la limite propre à l'employé ───────────────────────
        if employe_id:
            employe = request.env['lagunes.employe'].sudo().browse(employe_id)
            if employe.exists():
                max_employe = max(1, employe.max_commandes_par_jour or 1)
                peut_pour_autres = employe.peut_commander_pour_autres
            else:
                employe = None
                max_employe = entreprise.max_orders_per_session or 1
                peut_pour_autres = False
        else:
            max_employe = entreprise.max_orders_per_session or 1
            peut_pour_autres = False

        # ── Compter les commandes déjà passées aujourd'hui ───────────────
        if employe and employe.exists():
            commandes_aujourd_hui = request.env['lagunes.commande'].sudo().search_count([
                ('company_id', '=', request.website.company_id.id),
                ('entreprise_id', '=', entreprise_id),
                ('date', '=', today),
                ('employee_name', '=', employe.display_name_full),
                ('state', '!=', 'cancelled'),
            ])
        else:
            commandes_aujourd_hui = request.session.get('cantine_session_order_count', 0)

        # ── Vérification limite ──────────────────────────────────────────
        if commandes_aujourd_hui >= max_employe:
            return {
                'success': False,
                'message': (
                    f'Vous avez déjà passé {commandes_aujourd_hui} commande(s) aujourd\'hui. '
                    f'Limite autorisée : {max_employe} commande(s) par jour.'
                )
            }

        # ── Vérification : commande pour autre personne autorisée ? ──────
        order_for_other = bool(order_for_other)
        ordered_for_name = (ordered_for_name or '').strip()
        commande_pour_autre = (commandes_aujourd_hui >= 1)

        # Si l'utilisateur veut commander pour quelqu'un d'autre mais n'a pas le droit
        if (order_for_other or commande_pour_autre) and not peut_pour_autres:
            return {
                'success': False,
                'message': 'Vous n\'êtes pas autorisé à commander pour d\'autres personnes.'
            }

        require_other_name = commande_pour_autre or order_for_other
        if require_other_name and not ordered_for_name:
            return {
                'success': False,
                'message': "Veuillez renseigner le nom de la personne pour qui vous passez cette commande.",
            }

        # ── Avertissement pour commande supplémentaire ───────────────────
        message_avertissement = None
        if commande_pour_autre:
            message_avertissement = (
                f"⚠️ Vous avez déjà passé {commandes_aujourd_hui} commande(s) aujourd'hui. "
                f"Cette commande ({commandes_aujourd_hui + 1}/{max_employe}) "
                "est pour le compte d'une autre personne."
            )

        # ── Vérification limite globale entreprise ───────────────────────
        if entreprise.max_orders_per_day > 0:
            total = request.env['lagunes.commande'].sudo().search_count([
                ('company_id', '=', request.website.company_id.id),
                ('entreprise_id', '=', entreprise_id),
                ('date', '=', today),
                ('state', '!=', 'cancelled'),
            ])
            if total >= entreprise.max_orders_per_day:
                return {
                    'success': False,
                    'message': f'Limite journalière de {entreprise.max_orders_per_day} commande(s) atteinte pour votre entreprise.'
                }

        if not plats_choisis:
            return {'success': False, 'message': 'Veuillez sélectionner au moins un plat.'}

        try:
            week_menu = request.env['lagunes.week.menu'].sudo().browse(int(week_menu_id)) if week_menu_id else None

            entree_id = plats_choisis.get('entree')
            resistance_id = plats_choisis.get('resistance')
            dessert_id = plats_choisis.get('dessert')

            plat_principal_id = resistance_id or entree_id or dessert_id
            if not plat_principal_id:
                return {'success': False, 'message': 'Aucun plat sélectionné.'}

            vals = {
                'entreprise_id': entreprise_id,
                'week_menu_id': week_menu.id if week_menu else False,
                'day': str(day),
                'quantity': 1,
                'notes': notes or '',
                'date': today,
                'state': 'confirmed',
                'facturation_state': 'not_invoiced',
                'employee_name': employe_name,
                'ordered_for_name': ordered_for_name if require_other_name else False,
                'company_id': request.website.company_id.id,
            }

            # --- GESTION DES LIGNES (Flexible) ---
            line_vals = []
            if resistance_id:
                line_vals.append((0, 0, {'plat_id': int(resistance_id)}))
                vals['resistance_plat_id'] = int(resistance_id)

            # Récupération des côtés (Wizard) — side_X + side_X_type envoyés par le JS
            has_wizard_sides = any(
                k.startswith('side_') and not k.endswith('_type') and v
                for k, v in plats_choisis.items()
            )
            if has_wizard_sides:
                for k, v in plats_choisis.items():
                    if k.startswith('side_') and not k.endswith('_type') and v:
                        line_vals.append((0, 0, {'plat_id': int(v)}))
                        side_type = plats_choisis.get(k + '_type', '')
                        if side_type == 'entree':
                            vals['entree_plat_id'] = int(v)
                        elif side_type == 'dessert':
                            vals['dessert_plat_id'] = int(v)
            else:
                # Fallback : payload avec clés directes entree/dessert (ancien format)
                if entree_id:
                    line_vals.append((0, 0, {'plat_id': int(entree_id)}))
                    vals['entree_plat_id'] = int(entree_id)
                if dessert_id:
                    line_vals.append((0, 0, {'plat_id': int(dessert_id)}))
                    vals['dessert_plat_id'] = int(dessert_id)

            vals['line_ids'] = line_vals

            if option_ids:
                vals['option_ids'] = [(6, 0, [int(o) for o in option_ids])]


            commande = request.env['lagunes.commande'].sudo().create(vals)

            # Mise à jour compteur session
            new_count = request.session.get('cantine_session_order_count', 0) + 1
            request.session['cantine_session_order_count'] = new_count
            should_logout = False  # Déconnexion auto désactivée

            result = {
                'success': True,
                'message': f'Commande confirmée ! Référence : {commande.reference}',
                'commande_id': commande.id,
                'reference': commande.reference,
                'should_logout': should_logout,
                'commande_pour_autre': commande_pour_autre,
                'commandes_passees': commandes_aujourd_hui + 1,
                'max_commandes': max_employe,
            }
            if message_avertissement:
                result['avertissement'] = message_avertissement

            return result

        except Exception as e:
            return {'success': False, 'message': f'Erreur : {str(e)}'}

    # ================================================================== #
    #  HISTORIQUE DES COMMANDES                                           #
    # ================================================================== #

    @http.route('/cantine/commandes/list', type='http', auth='public', website=True)
    def my_orders_list(self, **kwargs):
        entreprise_id = request.session.get('cantine_entreprise_id')
        if not entreprise_id:
            return request.redirect('/cantine')

        employe_id = request.session.get('cantine_employe_id')
        employe_name = request.session.get('cantine_employe_name', '')

        domain = [
            ('company_id', '=', request.website.company_id.id),
            ('entreprise_id', '=', entreprise_id)
        ]
        if employe_id:
            employe = request.env['lagunes.employe'].sudo().browse(employe_id)
            if employe.exists():
                domain.append(('employee_name', '=', employe.display_name_full))

        commandes = request.env['lagunes.commande'].sudo().search(
            domain, order='date desc, create_date desc', limit=200
        )

        commandes_by_date = {}
        for cmd in commandes:
            d = cmd.date
            if d not in commandes_by_date:
                commandes_by_date[d] = []
            commandes_by_date[d].append(cmd)

        return request.render('lagunes_cantine.my_orders_list', {
            'commandes_by_date': commandes_by_date,
            'commandes': commandes,
            'employe_name': employe_name,
        })

    @http.route('/cantine/commandes/<int:commande_id>', type='http', auth='public', website=True)
    def view_order_detail(self, commande_id, **kwargs):
        entreprise_id = request.session.get('cantine_entreprise_id')
        if not entreprise_id:
            return request.redirect('/cantine')

        commande = request.env['lagunes.commande'].sudo().browse(commande_id)
        # Défense en profondeur : la commande doit appartenir à la société du
        # site courant ET à l'entreprise de la session (double contrôle).
        if (not commande.exists()
                or commande.company_id.id != request.website.company_id.id
                or int(commande.entreprise_id.id) != int(entreprise_id)):
            return request.not_found()

        return request.render('lagunes_cantine.order_detail', {'commande': commande})