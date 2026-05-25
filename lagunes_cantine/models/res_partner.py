# -*- coding: utf-8 -*-

import secrets
from datetime import datetime, time
from urllib.parse import unquote
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_cantine_client = fields.Boolean(
        string='Client Cantine',
        default=False,
        help='Cocher si ce partenaire est un client de la cantine d\'entreprise'
    )

    total_headcount = fields.Integer(
        string='Effectif total de la société',
        default=1,
        help='Nombre total d\'employés dans cette société (pour le calcul du taux de fréquentation)'
    )

    cantine_access_code = fields.Char(
        string='Code d\'accès',
        help='Code unique OBLIGATOIRE pour accéder au menu',
        copy=False
    )

    max_orders_per_day = fields.Integer(
        string='Limite de commandes par jour',
        compute='_compute_max_orders_per_day',
        store=True,
        readonly=True,
        help='Nombre maximum de commandes par jour pour l\'entreprise (égal au nombre d\'employés actifs)'
    )

    max_orders_per_session = fields.Integer(
        string='Limite de commandes par session employé',
        default=1,
        help='Nombre maximum de commandes qu\'un employé peut passer par session (0 ou 1 = déconnexion immédiate)'
    )

    # ------------------------------------------------------------------ #
    #  HEURE LIMITE DE COMMANDE (fonctionnalité 4)                        #
    # ------------------------------------------------------------------ #

    heure_limite_commande = fields.Float(
        string='Heure limite de commande',
        default=0.0,
        help='Heure limite pour passer commande (ex: 10.5 = 10h30). 0 = pas de limite.',
    )

    heure_limite_active = fields.Boolean(
        string='Activer l\'heure limite',
        default=False,
        help='Si coché, les employés ne pourront plus commander après l\'heure limite définie.',
    )

    heure_limite_display = fields.Char(
        string='Heure limite (affichage)',
        compute='_compute_heure_limite_display',
        store=False,
    )

    # ------------------------------------------------------------------ #
    #  INSCRIPTION EMPLOYÉS (fonctionnalité 3b/c)                         #
    # ------------------------------------------------------------------ #

    inscription_active = fields.Boolean(
        string='Lien d\'inscription actif',
        default=False,
        help='Activer pour permettre aux employés de s\'inscrire via le lien unique.',
    )

    inscription_token = fields.Char(
        string='Token d\'inscription',
        readonly=True,
        copy=False,
        help='Token unique pour le lien d\'inscription employés.',
    )

    inscription_url = fields.Char(
        string='Lien d\'inscription',
        compute='_compute_inscription_url',
        store=False,
    )

    # ------------------------------------------------------------------ #
    #  RELATIONS                                                           #
    # ------------------------------------------------------------------ #

    commande_ids = fields.One2many(
        'lagunes.commande',
        'entreprise_id',
        string='Commandes'
    )

    employe_ids = fields.One2many(
        'lagunes.employe',
        'entreprise_id',
        string='Employés',
    )
    
    # Relations v3.0
    week_menu_ids = fields.One2many(
        'lagunes.week.menu',
        'partner_id',
        string='Menus hebdomadaires',
        help='Menus de la semaine spécifiques à cette entreprise'
    )
    
    plat_type_rule_ids = fields.One2many(
        'lagunes.partner.plat.type.rule',
        'partner_id',
        string='Règles de types de plats',
        help='Règles d\'affichage et de configuration des types de plats'
    )
    
    menu_category_ids = fields.Many2many(
        'lagunes.menu.category',
        'lagunes_menu_category_partner_rel',
        'partner_id',
        'category_id',
        string='Catégories de menus accessibles'
    )

    commande_count = fields.Integer(
        string='Nombre de commandes',
        compute='_compute_commande_count',
        store=True
    )

    employe_count = fields.Integer(
        string='Nombre d\'employés',
        compute='_compute_employe_count',
        store=True,
    )
    
    # Stats v3.0
    week_menu_count = fields.Integer(
        string='Nombre de menus',
        compute='_compute_week_menu_count',
        store=True
    )
    
    plat_type_rule_count = fields.Integer(
        string='Règles de types',
        compute='_compute_plat_type_rule_count',
        store=True
    )

    # ------------------------------------------------------------------ #
    #  COMPUTE                                                             #
    # ------------------------------------------------------------------ #

    @api.depends('commande_ids')
    def _compute_commande_count(self):
        for partner in self:
            partner.commande_count = len(partner.commande_ids)

    @api.depends('employe_ids', 'employe_ids.active', 'max_orders_per_session')
    def _compute_max_orders_per_day(self):
        for partner in self:
            active_count = len(partner.employe_ids.filtered(lambda e: e.active))
            session_limit = max(1, partner.max_orders_per_session)
            partner.max_orders_per_day = active_count * session_limit

    @api.depends('employe_ids')
    def _compute_employe_count(self):
        for partner in self:
            partner.employe_count = len(partner.employe_ids)
    
    @api.depends('week_menu_ids')
    def _compute_week_menu_count(self):
        for partner in self:
            partner.week_menu_count = len(partner.week_menu_ids)
    
    @api.depends('plat_type_rule_ids')
    def _compute_plat_type_rule_count(self):
        for partner in self:
            partner.plat_type_rule_count = len(partner.plat_type_rule_ids)

    @api.depends('heure_limite_commande', 'heure_limite_active')
    def _compute_heure_limite_display(self):
        for partner in self:
            if partner.heure_limite_active and partner.heure_limite_commande > 0:
                h = int(partner.heure_limite_commande)
                m = int(round((partner.heure_limite_commande - h) * 60))
                partner.heure_limite_display = f"{h:02d}h{m:02d}"
            else:
                partner.heure_limite_display = "Pas de limite"

    @api.depends('inscription_token', 'inscription_active')
    def _compute_inscription_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for partner in self:
            if partner.inscription_token and partner.inscription_active:
                partner.inscription_url = f"{base_url}/cantine/inscription/{partner.inscription_token}"
            else:
                partner.inscription_url = ""

    # ------------------------------------------------------------------ #
    #  CONTRAINTES                                                         #
    # ------------------------------------------------------------------ #

    @api.constrains('cantine_access_code', 'is_cantine_client')
    def _check_access_code_required(self):
        for partner in self:
            if partner.is_cantine_client and not partner.cantine_access_code:
                raise ValidationError(
                    'Le code d\'accès est obligatoire pour les clients de la cantine.\n'
                    'Veuillez définir un code unique (ex: ACME2025, DIGIFAZ123, etc.)'
                )

    @api.constrains('cantine_access_code', 'is_cantine_client')
    def _check_access_code_unique(self):
        for partner in self:
            if partner.is_cantine_client and partner.cantine_access_code:
                duplicate = self.search([
                    ('id', '!=', partner.id),
                    ('cantine_access_code', '=', partner.cantine_access_code),
                    ('is_cantine_client', '=', True)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"Le code d'accès '{partner.cantine_access_code}' est déjà "
                        f"utilisé par {duplicate.name}.\n\n"
                        f"Veuillez choisir un code unique."
                    )

    @api.constrains('max_orders_per_day')
    def _check_max_orders_per_day(self):
        for partner in self:
            if partner.max_orders_per_day < 0:
                raise ValidationError(
                    'La limite de commandes par jour ne peut pas être négative.'
                )

    @api.constrains('heure_limite_commande')
    def _check_heure_limite(self):
        for partner in self:
            if partner.heure_limite_commande < 0 or partner.heure_limite_commande >= 24:
                raise ValidationError(
                    _('L\'heure limite doit être comprise entre 00:00 et 23:59.')
                )

    # ------------------------------------------------------------------ #
    #  ACTIONS                                                             #
    # ------------------------------------------------------------------ #

    def action_generer_token_inscription(self):
        """Génère ou régénère le token d'inscription."""
        for partner in self:
            partner.inscription_token = secrets.token_urlsafe(32)
            partner.inscription_active = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Lien généré'),
                'message': _('Le lien d\'inscription a été généré avec succès.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_desactiver_inscription(self):
        """Désactive le lien d'inscription sans supprimer le token."""
        for partner in self:
            partner.inscription_active = False

    def action_view_employes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employés - %s') % self.name,
            'res_model': 'lagunes.employe',
            'view_mode': 'list,form',
            'domain': [('entreprise_id', '=', self.id)],
            'context': {'default_entreprise_id': self.id},
        }

    # ------------------------------------------------------------------ #
    #  MÉTHODES PUBLIQUES                                                  #
    # ------------------------------------------------------------------ #

    def is_commande_allowed_now(self):
        """
        Vérifie si les commandes sont encore autorisées pour cette entreprise
        en fonction de l'heure limite configurée.
        Retourne (True, None) si autorisé, (False, 'HHhMM') si bloqué.
        """
        self.ensure_one()
        if not self.heure_limite_active or self.heure_limite_commande <= 0:
            return True, None

        now = datetime.now()
        current_float = now.hour + now.minute / 60.0

        if current_float >= self.heure_limite_commande:
            h = int(self.heure_limite_commande)
            m = int(round((self.heure_limite_commande - h) * 60))
            return False, f"{h:02d}h{m:02d}"

        return True, None

    @api.model
    def verify_cantine_access(self, access_code, email=None, mot_de_passe=None):
        """
        Vérifier l'accès avec le code entreprise + email employé.

        :param access_code: Code d'accès de l'entreprise
        :param email: Email de l'employé (obligatoire si des employés sont enregistrés)
        :param mot_de_passe: Mot de passe de l'employé (optionnel pour compatibilité)
        :return: dict avec statut et message
        """
        if not access_code or len(access_code.strip()) < 3:
            return {
                'success': False,
                'message': 'Veuillez entrer un code d\'accès valide (minimum 3 caractères)'
            }

        access_code = access_code.strip()

        # Chercher l'entreprise par code (insensible à la casse)
        entreprise = self.search([
            ('is_cantine_client', '=', True),
            ('cantine_access_code', '=ilike', access_code)
        ], limit=1)

        if not entreprise:
            return {
                'success': False,
                'message': 'Code d\'accès incorrect. Veuillez vérifier et réessayer.'
            }

        # Vérifier l'heure limite
        allowed, heure_limite = entreprise.is_commande_allowed_now()
        if not allowed:
            return {
                'success': False,
                'message': f'Les commandes sont closes depuis {heure_limite}. Revenez demain !'
            }

        # Si des employés sont enregistrés, vérifier l'email
        employe_count = self.env['lagunes.employe'].sudo().search_count([
            ('entreprise_id', '=', entreprise.id),
            ('active', '=', True),
        ])

        employe_id = None
        employe_name = None

        if employe_count > 0:
            # Authentification par email obligatoire
            if not email or not email.strip():
                return {
                    'success': False,
                    'message': 'Veuillez entrer votre adresse email.',
                    'require_email': True,
                }
            email = email.strip().lower()
            employe = self.env['lagunes.employe'].sudo().search([
                ('entreprise_id', '=', entreprise.id),
                ('email', '=ilike', email),
                ('active', '=', True),
            ], limit=1)
            if not employe:
                return {
                    'success': False,
                    'message': 'Email non reconnu pour cette entreprise. Contactez votre responsable.',
                    'require_email': True,
                }
            
            # Vérifier le mot de passe si un hash existe en base
            if employe.sudo().mot_de_passe:
                # Un hash existe → vérification obligatoire
                if not mot_de_passe or not employe.sudo()._check_password(mot_de_passe):
                    return {
                        'success': False,
                        'message': 'Email ou mot de passe incorrect.',
                        'require_email': True,
                    }
            
            employe_id = employe.id
            employe_name = employe.display_name_full

        return {
            'success': True,
            'message': f'Bienvenue chez {entreprise.name}',
            'entreprise_name': entreprise.name,
            'entreprise_id': entreprise.id,
            'max_orders_per_day': entreprise.max_orders_per_day,
            'max_orders_per_session': entreprise.max_orders_per_session or 1,
            'employe_id': employe_id,
            'employe_name': employe_name,
        }

    @api.model
    def get_by_inscription_token(self, token):
        """Retourne l'entreprise correspondant au token d'inscription."""
        if not token:
            return self.browse()
        token = unquote(token).strip().strip('/')
        if not token:
            return self.browse()
        entreprise = self.search([
            ('inscription_token', '=', token),
            ('inscription_active', '=', True),
            ('is_cantine_client', '=', True),
        ], limit=1)
        if entreprise:
            return entreprise
        return self.search([
            ('inscription_token', '=ilike', token),
            ('inscription_active', '=', True),
            ('is_cantine_client', '=', True),
        ], limit=1)
