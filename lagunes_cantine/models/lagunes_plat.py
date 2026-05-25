# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LagunesPlat(models.Model):
    _name = 'lagunes.plat'
    _description = 'Plat de la cantine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)',
         'Un plat avec ce nom existe déjà pour cette société.'),
    ]

    name = fields.Char(
        string='Nom du plat',
        required=True,
        translate=True,
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10,
        tracking=True
    )
    
    plat_type_id = fields.Many2one(
        'lagunes.plat.type',
        string='Type de plat',
        required=True,
        ondelete='restrict',
        help='Entrée, Plat de résistance, Dessert, etc.',
        tracking=True
    )

    # Indique si ce plat est un plat de résistance (calculé)
    is_plat_resistance = fields.Boolean(
        string='Est un plat de résistance',
        compute='_compute_is_plat_resistance',
        store=True,
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Produit principal',
        required=True,
        domain=[('type', '=', 'consu')],
        ondelete='restrict',
        tracking=True,
        help="Produit principal du plat. Pour un plat de résistance, c'est le plat principal "
             "(ex: Sauce djoumblé poulet fumé) ; l'accompagnement est défini à part.",
    )

    accompagnement_product_id = fields.Many2one(
        'product.product',
        string='Accompagnement',
        domain=[('type', '=', 'consu')],
        ondelete='restrict',
        tracking=True,
        help="Produit d'accompagnement servi avec le plat principal "
             "(ex: Riz Nature, Attiéké). Uniquement pour les plats de résistance.",
    )

    display_name_website = fields.Char(
        string='Nom affiché (site web)',
        compute='_compute_display_name_website',
        store=True,
        help="Concatène 'Plat principal / Accompagnement' pour l'affichage du site web. "
             "Pour les plats hors résistance, renvoie simplement le nom du plat.",
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    
    description = fields.Text(
        string='Description',
        translate=True
    )
    
    image_1920 = fields.Image(
        string='Image',
        related='product_id.image_1920',
        readonly=False
    )
    
    image_128 = fields.Image(
        string='Image (128x128)',
        related='product_id.image_128'
    )
    
    category_id = fields.Many2one(
        'product.category',
        string='Catégorie',
        related='product_id.categ_id',
        readonly=False
    )
    
    # TYPE DE MENU — UNIQUEMENT pour les plats de résistance
    menu_category_id = fields.Many2one(
        'lagunes.menu.category',
        string='Type de menu',
        ondelete='set null',
        help='Catégorie de menu (Africain, Européen, etc.).\n'
             'Disponible uniquement pour les plats de résistance.\n'
             'Définie une fois pour toutes sur le plat.',
        tracking=True
    )
    
    ingredient_ids = fields.One2many(
        'lagunes.plat.ingredient',
        'plat_id',
        string='Ingrédients nécessaires'
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True,
        tracking=True
    )

    is_global_available = fields.Boolean(
        string='Disponible hors menu (global)',
        default=False,
        help='Si coché, ce plat est disponible pour toutes les entreprises même s\'il n\'est pas au menu du jour.',
        tracking=True
    )
    
    option_ids = fields.Many2many(
        'lagunes.plat.option',
        'lagunes_plat_option_rel',
        'plat_id',
        'option_id',
        string='Options disponibles',
    )
    
    prix_unitaire = fields.Float(
        string='Prix unitaire',
        related='product_id.list_price',
        readonly=False,
    )
    
    ingredient_cost = fields.Float(
        string='Coût des ingrédients',
        compute='_compute_ingredient_cost',
        store=True
    )
    
    margin_percent = fields.Float(
        string='Marge (%)',
        compute='_compute_margin_percent',
        store=True
    )

    # ------------------------------------------------------------------ #
    #  COMPUTE                                                             #
    # ------------------------------------------------------------------ #

    @api.depends('plat_type_id', 'plat_type_id.name')
    def _compute_is_plat_resistance(self):
        for plat in self:
            name = (plat.plat_type_id.name or '').lower()
            plat.is_plat_resistance = (
                'sist' in name or 'principal' in name
            )

    @api.depends('name', 'is_plat_resistance', 'accompagnement_product_id', 'accompagnement_product_id.name')
    def _compute_display_name_website(self):
        for plat in self:
            if plat.is_plat_resistance and plat.accompagnement_product_id:
                plat.display_name_website = '%s / %s' % (plat.name or '', plat.accompagnement_product_id.name or '')
            else:
                plat.display_name_website = plat.name or ''

    @api.depends('ingredient_ids.ingredient_cost')
    def _compute_ingredient_cost(self):
        for plat in self:
            plat.ingredient_cost = sum(plat.ingredient_ids.mapped('ingredient_cost'))
    
    @api.depends('prix_unitaire', 'ingredient_cost')
    def _compute_margin_percent(self):
        for plat in self:
            if plat.ingredient_cost > 0:
                plat.margin_percent = ((plat.prix_unitaire - plat.ingredient_cost) / plat.ingredient_cost) * 100
            else:
                plat.margin_percent = 0

    # ------------------------------------------------------------------ #
    #  CONTRAINTES                                                         #
    # ------------------------------------------------------------------ #

    @api.constrains('prix_unitaire')
    def _check_prix_unitaire(self):
        for plat in self:
            if plat.prix_unitaire < 0:
                raise ValidationError(
                    _('Le prix unitaire ne peut pas être négatif pour le plat "%s"') % plat.name
                )

    @api.constrains('accompagnement_product_id', 'plat_type_id')
    def _check_accompagnement_resistance_only(self):
        """L'accompagnement n'est pertinent que sur un plat de résistance."""
        for plat in self:
            if plat.accompagnement_product_id and not plat.is_plat_resistance:
                raise ValidationError(
                    _("L'accompagnement ne peut être défini que sur un plat de résistance. "
                      "Le plat « %s » est de type « %s ».")
                    % (plat.name, plat.plat_type_id.name or '')
                )

    @api.constrains('menu_category_id', 'plat_type_id')
    def _check_menu_category_resistance_only(self):
        """Le type de menu ne peut être renseigné que sur les plats de résistance."""
        for plat in self:
            if plat.menu_category_id and not plat.is_plat_resistance:
                raise ValidationError(
                    _('Le type de menu ne peut être défini que sur un plat de résistance.\n'
                      'Le plat "%s" est de type "%s" — veuillez retirer le type de menu.')
                    % (plat.name, plat.plat_type_id.name)
                )

    # ------------------------------------------------------------------ #
    #  ONCHANGE                                                            #
    # ------------------------------------------------------------------ #

    @api.onchange('plat_type_id')
    def _onchange_plat_type_id(self):
        """Si le type change et n'est plus résistance, effacer menu_category_id."""
        name = (self.plat_type_id.name or '').lower()
        is_res = ('sist' in name or 'principal' in name)
        if not is_res and self.menu_category_id:
            self.menu_category_id = False
            return {
                'warning': {
                    'title': _('Type de menu effacé'),
                    'message': _('Le type de menu n\'est disponible que pour les plats de résistance. '
                                 'Le type de menu a été retiré automatiquement.')
                }
            }

    # ------------------------------------------------------------------ #
    #  CRUD                                                                #
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('product_id'):
                company_id = vals.get('company_id', self.env.company.id)
                product = self.env['product.product'].with_context(company_id=company_id).create({
                    'name': vals.get('name', 'Nouveau plat'),
                    'type': 'consu',
                    'sale_ok': True,
                    'purchase_ok': False,
                    'invoice_policy': 'order',
                    'taxes_id': [(5, 0, 0)],
                    'company_id': company_id,
                })
                vals['product_id'] = product.id
        return super().create(vals_list)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.name or self.name == 'Nouveau plat':
                self.name = self.product_id.name
    
    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for plat in self:
                if plat.product_id:
                    plat.product_id.name = vals['name']
        return res
