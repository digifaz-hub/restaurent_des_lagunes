# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from datetime import date, datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class LagunesCantineController(http.Controller):

    # ================================================================== #
    #  ACCUEIL & AUTHENTIFICATION                                          #
    # ================================================================== #

    @http.route('/cantine', type='http', auth='public', website=True)
    def cantine_home(self, **kwargs):
        entreprise_id = request.session.get('cantine_entreprise_id')
        if entreprise_id:
            if self._check_session_access(entreprise_id):
                return request.redirect('/cantine/menu')
            else:
                self._clear_session()
        return request.render('lagunes_cantine.cantine_home')

    # ── Rate limiting (brute-force protection) ────────────────────
    # ⚠️  PRODUCTION : Ce rate limiter est in-memory (reset au redémarrage,
    #    pas partagé entre workers). Pour un environnement multi-worker,
    #    migrer vers Redis, memcached ou ir.config_parameter.
    _login_attempts = {}   # {ip: [(timestamp, ...), ...]}
    _RATE_LIMIT_MAX = 5    # max attempts
    _RATE_LIMIT_WINDOW = 60  # seconds

    @classmethod
    def _check_rate_limit(cls, ip):
        """Returns True if the IP is rate-limited, False otherwise."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=cls._RATE_LIMIT_WINDOW)
        # Clean old entries
        attempts = cls._login_attempts.get(ip, [])
        attempts = [t for t in attempts if t > cutoff]
        cls._login_attempts[ip] = attempts
        if len(attempts) >= cls._RATE_LIMIT_MAX:
            return True
        attempts.append(now)
        cls._login_attempts[ip] = attempts
        return False

    @http.route('/cantine/verify_access', type='json', auth='public', website=True)
    def verify_access(self, access_code=None, email=None, mot_de_passe=None):
        # Rate limiting
        client_ip = request.httprequest.environ.get(
            'HTTP_X_FORWARDED_FOR', request.httprequest.remote_addr
        )
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        if self._check_rate_limit(client_ip):
            _logger.warning(
                'SECURITY: Rate limited IP %s on /cantine/verify_access',
                client_ip
            )
            return {
                'success': False,
                'message': 'Trop de tentatives. Veuillez patienter 1 minute avant de réessayer.',
            }

        result = request.env['res.partner'].sudo().verify_cantine_access(
            access_code=access_code,
            email=email,
            mot_de_passe=mot_de_passe,
        )
        if result.get('success'):
            _logger.info(
                'LOGIN OK: entreprise=%s ip=%s email=%s',
                result.get('entreprise_name', '?'), client_ip,
                request.params.get('email', '-')
            )
            request.session['cantine_entreprise_id'] = result['entreprise_id']
            request.session['cantine_access_code'] = access_code
            request.session['cantine_access_time'] = str(date.today())
            request.session['cantine_max_orders_session'] = result.get('max_orders_per_session', 1)
            request.session['cantine_session_order_count'] = 0
            request.session['cantine_login_time'] = str(datetime.now())
            if result.get('employe_id'):
                request.session['cantine_employe_id'] = result['employe_id']
                request.session['cantine_employe_name'] = result.get('employe_name', '')
        return result

    # ================================================================== #
    #  RÉCUPÉRATION DE MOT DE PASSE                                       #
    # ================================================================== #

    @http.route('/cantine/forgot-password', type='http', auth='public', website=True)
    def forgot_password(self, **kwargs):
        """Affiche le formulaire de récupération de mot de passe."""
        return request.render('lagunes_cantine.forgot_password')

    @http.route('/cantine/forgot-password/send', type='json', auth='public', website=True, csrf=False)
    def forgot_password_send(self, access_code=None, email=None):
        """Traite la demande de réinitialisation de mot de passe."""
        if not access_code or not email:
            return {
                'success': False,
                'message': 'Veuillez entrer le code d\'accès et votre email.'
            }

        access_code = access_code.strip()
        email = email.strip().lower()

        # Vérifier que l'entreprise existe *sur ce site* (filtre multi-société).
        entreprise = request.env['res.partner'].sudo().search([
            ('is_cantine_client', '=', True),
            ('cantine_access_code', '=ilike', access_code),
            ('company_id', 'in', [request.website.company_id.id, False]),
        ], limit=1)

        if not entreprise:
            return {
                'success': False,
                'message': 'Code d\'accès incorrect.'
            }

        # Vérifier que l'employé existe
        employe = request.env['lagunes.employe'].sudo().search([
            ('company_id', '=', request.website.company_id.id),
            ('entreprise_id', '=', entreprise.id),
            ('email', '=ilike', email),
            ('active', '=', True),
        ], limit=1)

        if not employe:
            # Pour des raisons de sécurité, ne pas révéler si l'email existe
            return {
                'success': True,
                'message': 'Si cet email existe, un lien de réinitialisation a été envoyé.'
            }

        # Rate limiting : vérifier que moins de 2 minutes se sont écoulées depuis la dernière demande
        if employe.reset_password_expiry:
            now = datetime.now()
            expiry = employe.reset_password_expiry.replace(tzinfo=None) if employe.reset_password_expiry.tzinfo else employe.reset_password_expiry
            # Le token dure 2h, donc il a été créé il y a (2h - temps_restant)
            deux_heures = timedelta(hours=2)
            token_age = deux_heures - (expiry - now)
            if token_age.total_seconds() < 120 and token_age.total_seconds() > 0:  # moins de 2 minutes
                return {
                    'success': True,  # ne pas révéler le blocage pour les raisons de sécurité
                    'message': 'Un lien de réinitialisation a été envoyé à votre email. Il expire dans 2 heures.'
                }

        try:
            employe.generate_reset_token()
            employe.send_reset_password_email()
            return {
                'success': True,
                'message': 'Un lien de réinitialisation a été envoyé à votre email. Il expire dans 2 heures.'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de l\'envoi de l\'email: {str(e)}'
            }

    @http.route('/cantine/forgot-password/reset/<string:token>', type='http', auth='public', website=True)
    def forgot_password_reset(self, token, **kwargs):
        """Affiche le formulaire de réinitialisation avec validation du token."""
        employe = request.env['lagunes.employe'].sudo().search([
            ('company_id', '=', request.website.company_id.id),
            ('reset_password_token', '=', token),
        ], limit=1)

        if not employe or not employe.is_reset_token_valid():
            return request.render('lagunes_cantine.error_page', {
                'error_message': 'Lien de réinitialisation invalide ou expiré. Veuillez recommencer.'
            })

        return request.render('lagunes_cantine.reset_password', {
            'employe': employe,
            'token': token,
        })

    @http.route('/cantine/forgot-password/reset/submit', type='json', auth='public', website=True, csrf=False)
    def forgot_password_reset_submit(self, token=None, new_password=None, confirm_password=None):
        """Traite la soumission du nouveau mot de passe."""
        if not token:
            return {'success': False, 'message': 'Token invalide.'}

        employe = request.env['lagunes.employe'].sudo().search([
            ('company_id', '=', request.website.company_id.id),
            ('reset_password_token', '=', token),
        ], limit=1)

        if not employe or not employe.is_reset_token_valid():
            return {
                'success': False,
                'message': 'Lien de réinitialisation invalide ou expiré.'
            }

        if not new_password or not confirm_password:
            return {'success': False, 'message': 'Veuillez entrer les deux mots de passe.'}

        if new_password != confirm_password:
            return {'success': False, 'message': 'Les mots de passe ne correspondent pas.'}

        if len(new_password) < 6:
            return {'success': False, 'message': 'Le mot de passe doit contenir au moins 6 caractères.'}

        try:
            employe.reset_password(new_password)
            return {
                'success': True,
                'message': 'Mot de passe réinitialisé avec succès. Connectez-vous maintenant.',
                'redirect_url': '/cantine'
            }
        except Exception as e:
            return {'success': False, 'message': f'Erreur: {str(e)}'}

    @http.route('/cantine/confirmation/<int:commande_id>', type='http', auth='public', website=True)
    def commande_confirmation(self, commande_id, **kwargs):
        entreprise_id = request.session.get('cantine_entreprise_id')
        commande = request.env['lagunes.commande'].sudo().browse(commande_id)
        # Sécurité multi-société : la commande doit exister, appartenir à la
        # société du site courant ET à l'entreprise de la session.
        if (not commande.exists()
                or commande.company_id.id != request.website.company_id.id
                or (entreprise_id and commande.entreprise_id.id != int(entreprise_id))):
            return request.render('lagunes_cantine.error_page', {'error_message': 'Commande non trouvée'})

        max_session = 1
        if entreprise_id:
            entreprise = request.env['res.partner'].sudo().browse(entreprise_id)
            max_session = entreprise.max_orders_per_session or 1

        current_count = request.session.get('cantine_session_order_count', 0)
        return request.render('lagunes_cantine.commande_confirmation', {
            'commande': commande,
            'limit_reached_session': (current_count >= max_session)
        })

    # ================================================================== #
    #  HISTORIQUE & DÉCONNEXION                                            #
    # ================================================================== #

    @http.route('/cantine/mes-commandes', type='http', auth='public', website=True)
    def mes_commandes(self, **kwargs):
        entreprise_id = request.session.get('cantine_entreprise_id')
        if not entreprise_id:
            return request.redirect('/cantine')
        entreprise = request.env['res.partner'].sudo().browse(entreprise_id)
        commandes = request.env['lagunes.commande'].sudo().search([
            ('company_id', '=', request.website.company_id.id),
            ('entreprise_id', '=', entreprise_id),
        ], order='date desc, create_date desc', limit=100)
        return request.render('lagunes_cantine.mes_commandes', {
            'commandes': commandes,
            'entreprise': entreprise,
        })

    @http.route('/cantine/logout', type='http', auth='public', website=True)
    def cantine_logout(self, **kwargs):
        self._clear_session()
        return request.redirect('/cantine')

    # ================================================================== #
    #  INSCRIPTION EMPLOYÉS                                                #
    # ================================================================== #

    @http.route('/cantine/inscription/<string:token>', type='http', auth='public', website=True)
    def inscription_employe(self, token, **kwargs):
        entreprise = request.env['res.partner'].sudo().get_by_inscription_token(token)
        # Sécurité multi-société : on n'accepte un token d'inscription que s'il
        # correspond à une entreprise de la même société que le site courant
        # (ou une entreprise globale sans company_id).
        website_company_id = request.website.company_id.id
        if (not entreprise
                or (entreprise.company_id
                    and entreprise.company_id.id != website_company_id)):
            return request.render('lagunes_cantine.error_page', {
                'error_message': 'Lien d\'inscription invalide ou expiré.'
            })
        return request.render('lagunes_cantine.inscription_employe', {
            'entreprise': entreprise,
            'token': token,
        })

    @http.route('/cantine/inscription/submit', type='json', auth='public', website=True)
    def inscription_employe_submit(self, token, nom, prenom, email, mot_de_passe):
        entreprise = request.env['res.partner'].sudo().get_by_inscription_token(token)
        website_company_id = request.website.company_id.id
        # Même contrôle que GET : le token doit correspondre à une entreprise
        # de la société du site courant.
        if (not entreprise
                or (entreprise.company_id
                    and entreprise.company_id.id != website_company_id)):
            return {'success': False, 'message': 'Lien d\'inscription invalide ou expiré.'}

        nom = (nom or '').strip()
        prenom = (prenom or '').strip()
        email = (email or '').strip().lower()
        mot_de_passe = (mot_de_passe or '').strip()

        if not nom or not prenom or not email or not mot_de_passe:
            return {'success': False, 'message': 'Tous les champs sont obligatoires.'}

        if '@' not in email:
            return {'success': False, 'message': 'Adresse email invalide.'}

        if len(mot_de_passe) < 6:
            return {'success': False, 'message': 'Le mot de passe doit contenir au moins 6 caractères.'}

        existing = request.env['lagunes.employe'].sudo().search([
            ('company_id', '=', request.website.company_id.id),
            ('entreprise_id', '=', entreprise.id),
            ('email', '=ilike', email),
        ], limit=1)
        if existing:
            return {
                'success': False,
                'message': 'Cette adresse email est déjà enregistrée pour cette entreprise.'
            }

        try:
            # Créer l'employé, puis hacher le mot de passe
            employe = request.env['lagunes.employe'].sudo().create({
                'nom': nom,
                'prenom': prenom,
                'email': email,
                'entreprise_id': entreprise.id,
                'active': True,
            })
            # Hacher et sauvegarder le mot de passe
            employe._set_password(mot_de_passe)
            
            return {
                'success': True,
                'message': f'Inscription réussie ! Bienvenue {prenom} {nom}.',
                'employe_id': employe.id,
            }
        except Exception as e:
            return {'success': False, 'message': f'Erreur lors de l\'inscription : {str(e)}'}

    # ================================================================== #
    #  HELPERS PRIVÉS                                                      #
    # ================================================================== #

    def _clear_session(self):
        entreprise_id = request.session.get('cantine_entreprise_id')
        keys_to_remove = [
            'cantine_entreprise_id', 'cantine_access_code',
            'cantine_access_time', 'cantine_max_orders_session',
            'cantine_session_order_count', 'cantine_employe_id',
            'cantine_employe_name',
        ]
        if entreprise_id:
            keys_to_remove.append(f'cantine_commanded_{entreprise_id}')
        for key in keys_to_remove:
            request.session.pop(key, None)

    def _check_session_access(self, entreprise_id):
        session_entreprise = request.session.get('cantine_entreprise_id')
        access_code = request.session.get('cantine_access_code')
        access_time = request.session.get('cantine_access_time')
        session_login_time = request.session.get('cantine_login_time')
        
        if not session_entreprise or not access_code or not access_time:
            return False
        if not session_entreprise or int(session_entreprise) != int(entreprise_id):
            return False
        try:
            access_date = date.fromisoformat(access_time)
            if access_date != date.today():
                return False
        except ValueError:
            return False
        
        # Vérifier que la session n'est pas antérieure au dernier changement de mot de passe
        employe_id = request.session.get('cantine_employe_id')
        if employe_id and session_login_time:
            employe = request.env['lagunes.employe'].sudo().browse(employe_id)
            if employe.exists() and employe.password_last_changed:
                try:
                    session_time = datetime.fromisoformat(session_login_time)
                    if employe.password_last_changed > session_time:
                        return False  # forcer reconnexion
                except (ValueError, TypeError):
                    return False
        
        return True