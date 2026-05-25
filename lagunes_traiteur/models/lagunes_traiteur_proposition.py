# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LagunesTraiteurProposition(models.Model):
    _name = 'lagunes.traiteur.proposition'
    _description = 'Proposition de Menu Traiteur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )
    demande_id = fields.Many2one(
        'lagunes.traiteur.demande',
        string='Demande',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    company_id = fields.Many2one(
        related='demande_id.company_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True,
    )
    partner_email = fields.Char(
        string='Email destinataire',
        required=True,
        tracking=True,
        help="Adresse à laquelle la proposition sera envoyée.",
    )
    nom_contact = fields.Char(related='demande_id.nom_contact', readonly=True)
    prenom_contact = fields.Char(related='demande_id.prenom_contact', readonly=True)

    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    nb_personnes = fields.Integer(
        string='Nombre de personnes',
        default=1,
        tracking=True,
    )

    line_ids = fields.One2many(
        'lagunes.traiteur.proposition.line',
        'proposition_id',
        string='Éléments du menu',
        copy=True,
    )

    notes = fields.Html(
        string='Notes / Présentation',
        help="Texte d'accompagnement libre intégré dans le PDF et l'email.",
    )

    montant_total = fields.Monetary(
        string='Montant total',
        compute='_compute_montant_total',
        currency_field='currency_id',
        store=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('sent', 'Envoyée'),
            ('accepted', 'Acceptée'),
            ('refused', 'Refusée'),
        ],
        string='Statut',
        default='draft',
        required=True,
        tracking=True,
    )
    date_envoi = fields.Datetime(string='Envoyée le', readonly=True, copy=False)

    # ------------------------------------------------------------------ #
    #  CRUD                                                                #
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                seq = self.env['ir.sequence'].next_by_code('lagunes.traiteur.proposition')
                vals['name'] = seq or _('Nouveau')
            # Pré-remplir email et nb_personnes depuis la demande si non fournis
            if vals.get('demande_id'):
                demande = self.env['lagunes.traiteur.demande'].browse(vals['demande_id'])
                if not vals.get('partner_email') and demande.email_contact:
                    vals['partner_email'] = demande.email_contact
                if not vals.get('nb_personnes') and demande.nb_personnes:
                    vals['nb_personnes'] = demande.nb_personnes
        return super().create(vals_list)

    # ------------------------------------------------------------------ #
    #  COMPUTE                                                             #
    # ------------------------------------------------------------------ #

    @api.depends('line_ids.sous_total')
    def _compute_montant_total(self):
        for rec in self:
            rec.montant_total = sum(rec.line_ids.mapped('sous_total'))

    # ------------------------------------------------------------------ #
    #  ACTIONS                                                             #
    # ------------------------------------------------------------------ #

    def action_send_email(self):
        """Ouvre le composeur d'email pré-rempli avec le template de proposition."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Vous devez ajouter au moins un élément au menu avant de l'envoyer."))
            
        template = self.env.ref(
            'lagunes_traiteur.email_template_proposition_menu',
            raise_if_not_found=False,
        )
        ctx = {
            'default_model': 'lagunes.traiteur.proposition',
            'default_res_ids': self.ids,
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'mark_proposition_as_sent': True,
            'force_email': True,
        }
        return {
            'name': _('Envoyer la proposition de menu'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def action_mark_sent(self):
        for rec in self:
            rec.write({'state': 'sent', 'date_envoi': fields.Datetime.now()})

    def action_mark_accepted(self):
        self.write({'state': 'accepted'})

    def action_mark_refused(self):
        self.write({'state': 'refused'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_print(self):
        self.ensure_one()
        return self.env.ref('lagunes_traiteur.action_report_traiteur_proposition_menu').report_action(self)
