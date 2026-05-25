# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LaguesMenuCategory(models.Model):
    """Catégories de menus : Africain, Européen, Végétarien, etc."""
    
    _name = 'lagunes.menu.category'
    _description = 'Catégorie de menus'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Nom',
        required=True,
        translate=True,
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10,
        tracking=True
    )
    
    description = fields.Text(
        string='Description',
        translate=True
    )
    
    icon = fields.Char(
        string='Icône (FontAwesome)',
        help='ex: fa-leaf pour végétarien',
        tracking=True
    )
    
    color = fields.Char(
        string='Couleur (hex)',
        help='Code couleur hex (ex: #FF5733) ou classe CSS',
        tracking=True
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True,
        tracking=True
    )
    
    # Restriction d'accès par entreprise
    restricted_to_partners = fields.Boolean(
        string='Accès restreint',
        default=False,
        help='Si coché, cette catégorie n\'est accessible que pour certaines entreprises',
        tracking=True
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        'lagunes_menu_category_partner_rel',
        'category_id',
        'partner_id',
        string='Entreprises autorisées',
        domain=[('is_cantine_client', '=', True)]
    )
    
    # Stats utilisés pour les dashboards
    menu_line_count = fields.Integer(
        string='Nombre de lignes de menu',
        compute='_compute_menu_line_count',
        store=True
    )
    
    @api.depends('partner_ids')
    def _compute_menu_line_count(self):
        for category in self:
            category.menu_line_count = self.env['lagunes.week.menu.line'].search_count([
                ('menu_category_id', '=', category.id)
            ])
    
    @api.constrains('color')
    def _check_color(self):
        """Valider que la couleur est au format hex ou classe CSS valide"""
        import re
        for category in self:
            if category.color:
                # Vérifier format hex (#RRGGBB ou #RGB)
                if not re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$|^[a-z\-]+$', category.color):
                    raise ValidationError(
                        _('La couleur doit être au format hex (#RRGGBB) ou classe CSS valide')
                    )
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'La catégorie de menu doit être unique'),
    ]
