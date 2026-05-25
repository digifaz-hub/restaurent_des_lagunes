# -*- coding: utf-8 -*-

import secrets
from datetime import timedelta, datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# passlib est livré avec Odoo, pas besoin de l'installer
from passlib.context import CryptContext

_crypt_context = CryptContext(schemes=['pbkdf2_sha512'], deprecated='auto')


class LagunesEmploye(models.Model):
    _name = 'lagunes.employe'
    _description = 'Employé cantine'
    _order = 'nom, prenom'
    _rec_name = 'display_name_full'

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # ------------------------------------------------------------------ #
    #  CHAMPS                                                              #
    # ------------------------------------------------------------------ #

    nom = fields.Char(string='Nom', required=True)
    prenom = fields.Char(string='Prénom', required=True)

    email = fields.Char(
        string='Email',
        required=True,
        index=True,
    )

    display_name_full = fields.Char(
        string='Nom complet',
        compute='_compute_display_name_full',
        store=True,
    )

    entreprise_id = fields.Many2one(
        'res.partner',
        string='Entreprise',
        required=True,
        domain=[('is_cantine_client', '=', True)],
        ondelete='cascade',
        index=True,
    )

    active = fields.Boolean(
        string='Actif',
        default=True,
        help='Désactiver pour interdire la connexion à cet employé',
    )

    mot_de_passe = fields.Char(
        string='Mot de passe (hash)',
        copy=False,
        groups='base.group_system',
        help='Hash bcrypt du mot de passe — ne jamais exposer',
    )

    # ------------------------------------------------------------------ #
    #  NOUVEAU : Peut-il commander pour quelqu'un d'autre ?               #
    # ------------------------------------------------------------------ #
    peut_commander_pour_autres = fields.Boolean(
        string='Peut commander pour d\'autres personnes',
        default=False,
        help=(
            'Si activé, cet employé peut passer des commandes supplémentaires '
            'pour le compte d\'autres personnes de son entreprise.'
        ),
    )

    nb_personnes_autorisees = fields.Integer(
        string='Nombre de personnes supplémentaires',
        default=1,
        help=(
            'Nombre de personnes supplémentaires pour lesquelles cet employé '
            'peut commander (en plus de lui-même).\n'
            'Exemple : 2 = il peut commander pour lui + 2 autres personnes = 3 commandes/jour.'
        ),
    )

    # ------------------------------------------------------------------ #
    #  Limite de commandes par jour (calculée automatiquement)            #
    # ------------------------------------------------------------------ #
    max_commandes_par_jour = fields.Integer(
        string='Commandes max par jour',
        compute='_compute_max_commandes_par_jour',
        store=True,
        help=(
            'Calculé automatiquement : 1 (lui-même) + nombre de personnes autorisées.\n'
            'Ce champ est géré automatiquement.'
        ),
    )

    # Récupération de mot de passe
    reset_password_token = fields.Char(
        string='Token de réinitialisation',
        copy=False,
        readonly=True,
        help='Token unique pour réinitialiser le mot de passe'
    )

    reset_password_expiry = fields.Datetime(
        string='Expiration du token',
        copy=False,
        readonly=True,
        help='Date/heure d\'expiration du token de réinitialisation'
    )

    date_inscription = fields.Date(
        string='Date d\'inscription',
        default=fields.Date.today,
        readonly=True,
    )

    password_last_changed = fields.Datetime(
        string='Dernier changement de mot de passe',
        readonly=True,
        copy=False,
        help='Utilisé pour invalider les sessions après un changement de mot de passe',
    )

    commande_count = fields.Integer(
        string='Commandes',
        compute='_compute_commande_count',
        store=False,
    )

    # Règles de types de plats autorisés (override entreprise)
    plat_type_ids = fields.Many2many(
        'lagunes.plat.type',
        'lagunes_employe_plat_type_rel',
        'employe_id',
        'plat_type_id',
        string='Types de plats autorisés',
        help='Types de plats que cet employé peut commander. Si vide, utilise les règles de l\'entreprise.',
    )

    menu_category_ids = fields.Many2many(
        'lagunes.menu.category',
        'lagunes_employe_menu_category_rel',
        'employe_id',
        'category_id',
        string='Catégories de menus autorisées',
        help='Catégories de menus (Africain, Européen, etc.) que cet employé peut commander. Si vide, utilise les règles de l\'entreprise.',
    )

    # ------------------------------------------------------------------ #
    #  COMPUTE                                                             #
    # ------------------------------------------------------------------ #

    @api.depends('nom', 'prenom')
    def _compute_display_name_full(self):
        for emp in self:
            emp.display_name_full = f"{emp.prenom or ''} {emp.nom or ''}".strip()

    @api.depends('peut_commander_pour_autres', 'nb_personnes_autorisees')
    def _compute_max_commandes_par_jour(self):
        for emp in self:
            if emp.peut_commander_pour_autres:
                emp.max_commandes_par_jour = 1 + max(1, emp.nb_personnes_autorisees or 1)
            else:
                emp.max_commandes_par_jour = 1

    def _compute_commande_count(self):
        for emp in self:
            emp.commande_count = self.env['lagunes.commande'].search_count([
                ('entreprise_id', '=', emp.entreprise_id.id),
                ('employee_name', 'ilike', emp.display_name_full),
            ])

    # ------------------------------------------------------------------ #
    #  CONTRAINTES                                                         #
    # ------------------------------------------------------------------ #

    @api.constrains('email', 'entreprise_id')
    def _check_email_unique_per_entreprise(self):
        for emp in self:
            duplicate = self.search([
                ('id', '!=', emp.id),
                ('email', '=ilike', emp.email),
                ('entreprise_id', '=', emp.entreprise_id.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    _('L\'email %(email)s est déjà enregistré pour %(entreprise)s.')
                    % {'email': emp.email, 'entreprise': emp.entreprise_id.name}
                )

    @api.constrains('nb_personnes_autorisees')
    def _check_nb_personnes(self):
        for emp in self:
            if emp.peut_commander_pour_autres and emp.nb_personnes_autorisees < 1:
                raise ValidationError(
                    _('Le nombre de personnes supplémentaires doit être au moins 1.')
                )

    # ------------------------------------------------------------------ #
    #  RÉINITIALISATION DE MOT DE PASSE                                   #
    # ------------------------------------------------------------------ #

    def generate_reset_token(self):
        """Génère un token de réinitialisation valide 2h."""
        for emp in self:
            emp.reset_password_token = secrets.token_urlsafe(32)
            emp.reset_password_expiry = fields.Datetime.now() + timedelta(hours=2)

    def is_reset_token_valid(self):
        """Vérifie si le token est valide et non expiré."""
        self.ensure_one()
        if not self.reset_password_token:
            return False
        if not self.reset_password_expiry:
            return False
        return fields.Datetime.now() <= self.reset_password_expiry

    def _set_password(self, plain_password):
        """Hache et sauvegarde le mot de passe."""
        self.ensure_one()
        self.mot_de_passe = _crypt_context.hash(plain_password)

    def _check_password(self, plain_password):
        """Vérifie un mot de passe en clair contre le hash stocké."""
        self.ensure_one()
        if not self.mot_de_passe:
            return False
        try:
            valid, new_hash = _crypt_context.verify_and_update(
                plain_password, self.mot_de_passe
            )
            # Rehacher si l'algo est obsolète
            if valid and new_hash:
                self.mot_de_passe = new_hash
            return valid
        except Exception:
            return False

    def send_reset_password_email(self):
        """Envoie un email avec le lien de réinitialisation."""
        self.ensure_one()
        if not self.reset_password_token:
            self.generate_reset_token()
        
        # Construire l'URL du lien de réinitialisation
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        reset_url = f"{base_url}/cantine/forgot-password/reset/{self.reset_password_token}"
        
        subject = _('Réinitialisation de votre mot de passe')
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #16166d 0%, #0f0f52 100%); color: white; padding: 30px 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 28px; font-weight: 600; }}
        .header p {{ margin: 5px 0 0 0; font-size: 14px; opacity: 0.9; }}
        .content {{ background-color: white; padding: 40px 30px; }}
        .greeting {{ color: #16166d; font-size: 18px; font-weight: 600; margin-bottom: 20px; }}
        .message {{ color: #555; font-size: 14px; margin-bottom: 30px; line-height: 1.8; }}
        .cta-button {{ display: inline-block; background-color: #16166d; color: white; padding: 14px 35px; text-decoration: none; border-radius: 5px; font-weight: 600; margin: 30px 0; transition: all 0.3s ease; }}
        .warning {{ background-color: #fff3cd; border-left: 4px solid #f5a821; padding: 15px; margin: 20px 0; color: #856404; font-size: 13px; border-radius: 4px; }}
        .expiry {{ color: #787b2b; font-weight: 600; font-size: 13px; }}
        .footer {{ background-color: #f8f9fa; padding: 30px 20px; text-align: center; color: #666; font-size: 12px; border-top: 1px solid #e0e0e0; }}
        .divider {{ background-color: #f5a821; height: 3px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍽️ Restaurant des Lagunes</h1>
            <p>Cantine d'entreprise</p>
        </div>
        
        <div class="content">
            <p class="greeting">Bonjour {self.display_name_full},</p>
            
            <p class="message">
                Vous avez demandé une réinitialisation de mot de passe pour votre compte 
                <strong>MyCantine</strong> de <strong>{self.entreprise_id.name}</strong>.
            </p>
            
            <div style="text-align: center;">
                <a href="{reset_url}" class="cta-button">
                    🔐 Réinitialiser mon mot de passe
                </a>
            </div>
            
            <div class="divider"></div>
            
            <div class="warning">
                <strong>Sécurité ⚠️</strong><br/>
                <span class="expiry">Ce lien expire dans 2 heures.</span>
                Si vous n'êtes pas à l'origine de cette demande, 
                ignorez ce message et votre mot de passe restera inchangé.
            </div>
            
            <p style="color: #999; font-size: 12px; margin-top: 30px;">
                Vous ne pouvez pas cliquer sur le bouton ? Copiez ce lien dans votre navigateur :<br/>
                <code style="background-color: #f0f0f0; padding: 8px; display: inline-block; border-radius: 3px; color: #666; word-break: break-all;">
                    {reset_url}
                </code>
            </p>
        </div>
        
        <div class="footer">
            <p>
                © 2026 <strong>Restaurant des Lagunes</strong> — Cantine d'entreprise<br/>
            </p>
        </div>
    </div>
</body>
</html>
        """
        
        mail_values = {
            'subject': subject,
            'email_to': self.email,
            'email_from': self.env.user.email_formatted or 'noreply@example.com',
            'body_html': body_html,
        }
        self.env['mail.mail'].sudo().create(mail_values).send()

    def reset_password(self, new_password):
        """Réinitialise le mot de passe et invalide le token."""
        self.ensure_one()
        if not self.is_reset_token_valid():
            raise ValidationError(_('Le lien de réinitialisation est expiré ou invalide.'))
        
        if len(new_password) < 6:
            raise ValidationError(_('Le mot de passe doit contenir au moins 6 caractères.'))
        
        self._set_password(new_password)
        self.write({
            'reset_password_token': False,
            'reset_password_expiry': False,
            'password_last_changed': fields.Datetime.now(),
        })
        
        # Envoyer un email de confirmation
        self._send_password_changed_email()

    def _send_password_changed_email(self):
        """Notifie l'employé que son mot de passe a été modifié."""
        self.ensure_one()
        
        subject = _('Votre mot de passe a été modifié')
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #16166d 0%, #0f0f52 100%); color: white; padding: 30px 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 28px; font-weight: 600; }}
        .content {{ background-color: white; padding: 40px 30px; }}
        .greeting {{ color: #16166d; font-size: 18px; font-weight: 600; margin-bottom: 20px; }}
        .warning {{ background-color: #fff3cd; border-left: 4px solid #f5a821; padding: 15px; margin: 20px 0; color: #856404; font-size: 13px; border-radius: 4px; }}
        .footer {{ background-color: #f8f9fa; padding: 30px 20px; text-align: center; color: #666; font-size: 12px; border-top: 1px solid #e0e0e0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍽️ Restaurant des Lagunes</h1>
            <p>Cantine d'entreprise</p>
        </div>
        
        <div class="content">
            <p class="greeting">Bonjour {self.display_name_full},</p>
            
            <p>
                Votre mot de passe MyCantine a été <strong>modifié avec succès</strong> pour votre compte 
                <strong>{self.entreprise_id.name}</strong>.
            </p>
            
            <div class="warning">
                <strong>⚠️ Sécurité</strong><br/>
                Si vous n'êtes pas à l'origine de cette modification, contactez immédiatement votre responsable.
            </div>
            
            <p style="color: #999; font-size: 13px; margin-top: 30px;">
                {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
            </p>
        </div>
        
        <div class="footer">
            <p>© 2026 <strong>Restaurant des Lagunes</strong> — Cantine d'entreprise</p>
        </div>
    </div>
</body>
</html>
        """
        
        self.env['mail.mail'].sudo().create({
            'subject': subject,
            'email_to': self.email,
            'email_from': self.env.user.email_formatted or 'noreply@example.com',
            'body_html': body_html,
        }).send()

    # ------------------------------------------------------------------ #
    #  ACTIONS                                                             #
    # ------------------------------------------------------------------ #

    def action_desactiver(self):
        for emp in self:
            emp.active = False

    def action_activer(self):
        for emp in self:
            emp.active = True