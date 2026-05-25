# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LaguesPartnerPlatTypeRule(models.Model):
    """Règles d'affichage des types de plats par entreprise"""
    
    _name = 'lagunes.partner.plat.type.rule'
    _description = 'Règles d\'affichage des types de plats par entreprise'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'partner_id, sequence, plat_type_id'
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Entreprise',
        required=True,
        domain=[('is_cantine_client', '=', True)],
        ondelete='cascade',
        index=True,
        tracking=True
    )
    
    plat_type_id = fields.Many2one(
        'lagunes.plat.type',
        string='Type de plat',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    
    # Si obligatoire, ce type doit toujours être proposé
    is_mandatory = fields.Boolean(
        string='Obligatoire',
        default=False,
        help='Si coché, les employés doivent choisir dans ce type de plat',
        tracking=True
    )
    
    # Si proposé, ce type est optionnel
    is_proposed = fields.Boolean(
        string='Proposé',
        default=True,
        help='Si coché, ce type de plat est visible pour l\'entreprise',
        tracking=True
    )
    
    # Nombre de choix possibles (pour "plat de résistance" par exemple)
    max_choices = fields.Integer(
        string='Nombre de choix',
        default=1,
        help='Nombre de plats que l\'employé peut choisir dans ce type',
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10,
        tracking=True
    )
    
    notes = fields.Text(
        string='Notes',
        help='Notes internes sur cette règle'
    )
    
    # Nombres de commandes utilisant cette règle (stats)
    commande_count = fields.Integer(
        string='Commandes',
        compute='_compute_commande_count',
        store=True
    )
    
    plat_count = fields.Integer(
        string='Plats disponibles',
        compute='_compute_plat_count',
        store=True
    )
    
    @api.depends('plat_type_id')
    def _compute_plat_count(self):
        for rule in self:
            rule.plat_count = self.env['lagunes.plat'].search_count([
                ('plat_type_id', '=', rule.plat_type_id.id),
                ('active', '=', True),
            ])
    
    @api.depends('partner_id', 'plat_type_id')
    def _compute_commande_count(self):
        for rule in self:
            # Chercher les commandes de cette entreprise avec ce type de plat
            # On cherche dans les 3 champs: entree, resistance, dessert
            domain = [
                ('entreprise_id', '=', rule.partner_id.id),
                '|', '|',
                ('entree_plat_id.plat_type_id', '=', rule.plat_type_id.id),
                ('resistance_plat_id.plat_type_id', '=', rule.plat_type_id.id),
                ('dessert_plat_id.plat_type_id', '=', rule.plat_type_id.id),
            ]
            rule.commande_count = self.env['lagunes.commande'].search_count(domain)
    
    @api.constrains('max_choices')
    def _check_max_choices(self):
        for rule in self:
            if rule.max_choices < 0:
                raise ValidationError(
                    _('Le nombre de choix ne peut pas être négatif')
                )
            if rule.max_choices == 0 and rule.is_mandatory:
                raise ValidationError(
                    _('Un type obligatoire doit avoir au moins 1 choix possible')
                )
    
    @api.constrains('is_mandatory', 'is_proposed')
    def _check_mandatory_proposed(self):
        for rule in self:
            if rule.is_mandatory and not rule.is_proposed:
                # Auto-fixer : impossible d'être obligatoire si non proposé
                rule.is_proposed = True
    
    _sql_constraints = [
        ('unique_partner_type', 'unique(partner_id, plat_type_id)', 
         'Une règle par entreprise et par type de plat'),
    ]
