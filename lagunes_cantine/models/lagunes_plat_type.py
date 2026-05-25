# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LagunesPlatType(models.Model):
    """Types de plats : Entrée, Plat de résistance, Dessert"""
    
    _name = 'lagunes.plat.type'
    _description = 'Type de plat de cantine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Nom',
        required=True,
        translate=True,
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Séquence d\'affichage',
        default=10,
        tracking=True
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Description du type de plat pour les employés'
    )
    
    color = fields.Integer(
        string='Couleur (code hex)',
        help='Code couleur 0xRRGGBB pour l\'affichage',
        tracking=True
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True,
        tracking=True
    )
    
    # Stats
    plat_count = fields.Integer(
        string='Nombre de plats',
        compute='_compute_plat_count',
        store=True
    )
    
    menu_line_count = fields.Integer(
        string='Nombre de lignes de menu',
        compute='_compute_menu_line_count',
        store=True
    )
    
    @api.depends('active')
    def _compute_plat_count(self):
        for plat_type in self:
            plat_type.plat_count = self.env['lagunes.plat'].search_count([
                ('plat_type_id', '=', plat_type.id),
                ('active', '=', True),
            ])
    
    @api.depends('active')
    def _compute_menu_line_count(self):
        for plat_type in self:
            plat_type.menu_line_count = self.env['lagunes.week.menu.line'].search_count([
                ('plat_type_id', '=', plat_type.id)
            ])
    
    @api.constrains('color')
    def _check_color(self):
        """Valider que la couleur est un nombre valide"""
        for plat_type in self:
            if plat_type.color < 0 or plat_type.color > 0xFFFFFF:
                raise ValidationError(
                    _('La couleur doit être entre 0 et 0xFFFFFF (format hex)')
                )
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Le type de plat doit être unique'),
    ]
