# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import logging
import json

_logger = logging.getLogger(__name__)



class LagunesCommandeLigne(models.Model):
    _name = 'lagunes.commande.ligne'
    _description = 'Ligne de commande cantine'

    commande_id = fields.Many2one('lagunes.commande', string='Commande', ondelete='cascade', required=True)
    company_id = fields.Many2one('res.company', related='commande_id.company_id', store=True, index=True)
    plat_id = fields.Many2one('lagunes.plat', string='Plat', required=True)

    plat_type_id = fields.Many2one('lagunes.plat.type', related='plat_id.plat_type_id', store=True)
    quantity = fields.Integer(string='Quantité', default=1)
    price_unit = fields.Float(string='Prix unitaire', digits='Product Price')
    price_subtotal = fields.Float(string='Sous-total', compute='_compute_price_subtotal', store=True)

    @api.onchange('plat_id')
    def _onchange_plat_id(self):
        if self.plat_id:
            self.price_unit = self.plat_id.prix_unitaire


    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit


class LagunesCommande(models.Model):

    _name = 'lagunes.commande'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Commande cantine'
    _order = 'date desc, create_date desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        index=True,
    )

    entreprise_id = fields.Many2one(
        'res.partner',
        string='Entreprise',
        required=True,
        domain=[('is_cantine_client', '=', True)],
        ondelete='restrict',
        index=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    date = fields.Date(
        string='Date de la commande',
        required=True,
        default=fields.Date.today,
        index=True,
        tracking=True
    )

    # === Champs pour menu complet hebdo ===
    week_menu_id = fields.Many2one(
        'lagunes.week.menu',
        string='Menu de la semaine',
        ondelete='restrict',
        help='Menu hebdomadaire correspondant',
        tracking=True
    )

    day = fields.Selection([
        ('0', 'Samedi'),
        ('1', 'Dimanche'),
        ('2', 'Lundi'),
        ('3', 'Mardi'),
        ('4', 'Mercredi'),
        ('5', 'Jeudi'),
        ('6', 'Vendredi'),
    ], string='Jour de la semaine', required=False, compute='_compute_day_from_date', store=True, tracking=True)

    menu_category_id = fields.Many2one(
        'lagunes.menu.category',
        string='Catégorie de menu',
        ondelete='set null',
        help='Catégorie choisie (Africain, Européen, etc.)',
        tracking=True
    )

    # Plats par type (1 par type)
    entree_plat_id = fields.Many2one(
        'lagunes.plat',
        string='Entrée',
        ondelete='restrict',
        help='Plat d\'entrée choisi',
        tracking=True
    )
    
    resistance_plat_id = fields.Many2one(
        'lagunes.plat',
        string='Plat de résistance',
        ondelete='restrict',
        help='Plat principal choisi',
        tracking=True
    )
    
    dessert_plat_id = fields.Many2one(
        'lagunes.plat',
        string='Dessert',
        ondelete='restrict',
        help='Dessert choisi',
        tracking=True
    )

    # Flags hors-menu par type
    entree_is_custom_choice = fields.Boolean(
        string='Entrée hors-menu',
        default=False,
        help='Indique si l\'entrée est choisie hors du menu du jour',
        tracking=True
    )
    
    resistance_is_custom_choice = fields.Boolean(
        string='Plat principal hors-menu',
        default=False,
        help='Indique si le plat principal est choisi hors du menu du jour',
        tracking=True
    )
    
    dessert_is_custom_choice = fields.Boolean(
        string='Dessert hors-menu',
        default=False,
        help='Indique si le dessert est choisi hors du menu du jour',
        tracking=True
    )

    quantity = fields.Integer(
        string='Quantité',
        default=1,
        required=True,
        tracking=True
    )

    option_ids = fields.Many2many(
        'lagunes.plat.option',
        'lagunes_commande_option_rel',
        'commande_id',
        'option_id',
        string='Options',
    )

    line_ids = fields.One2many(
        'lagunes.commande.ligne',
        'commande_id',
        string='Lignes de commande',
        copy=True
    )

    display_menu = fields.Char(
        string='Menu consommé',
        compute='_compute_display_menu',
        store=True,
        help="Résumé textuel du menu pour les rapports (Entrée + Plat + Dessert)"
    )

    prix_total = fields.Float(
        string='Prix total',
        compute='_compute_prix_total',
        store=True,
        tracking=True,
        help="Montant total de la commande (Plats + Options) x Quantité"
    )


    notes = fields.Text(string='Notes / Instructions spéciales')

    employee_name = fields.Char(
        string='Nom de l\'employé',
        help='Nom de l\'employé qui a passé la commande',
    )

    ordered_for_name = fields.Char(
        string='Commande pour',
        help='Nom de la personne bénéficiaire si la commande est passée pour quelqu’un d’autre.',
        tracking=True,
    )

    state = fields.Selection([
        ('draft',      'Brouillon'),
        ('confirmed',  'Confirmée'),
        ('preparing',  'En préparation'),
        ('ready',      'Prêt'),
        ('delivered',  'Livré'),
        ('cancelled',  'Annulé'),
    ], string='Statut', default='draft', required=True, index=True, tracking=True)

    # ═══════════════════════════════════════════════════════════════════════
    # GESTION STOCK MARCHÉ - IDEMPOTENCE ET CONTRÔLES
    # ═══════════════════════════════════════════════════════════════════════

    is_stock_deducted = fields.Boolean(
        string='Stock déduit',
        default=False,
        copy=False,
        readonly=True,
        help='Marqueur technique : True si les ingrédients ont déjà été déduits du stock marché',
    )

    stock_insufficient = fields.Boolean(
        string='Stock insuffisant',
        default=False,
        copy=False,
        readonly=True,
        help='True si le stock était insuffisant lors de la déduction (forcé par utilisateur)',
    )

    stock_forced_by_id = fields.Many2one(
        comodel_name='res.users',
        string='Forçage par',
        readonly=True,
        help='Utilisateur qui a forcé la déduction malgré stock insuffisant',
    )

    stock_forced_date = fields.Datetime(
        string='Date forçage',
        readonly=True,
        help='Date et heure du forçage stock insuffisant',
    )

    stock_insufficient_details = fields.Text(
        string='Détails manquants',
        readonly=True,
        help='JSON des articles manquants lors de la déduction (article, demandé, disponible)',
    )

    stock_deduction_date = fields.Datetime(
        string='Date déduction stock',
        readonly=True,
        help='Date et heure de la dernière déduction de stock',
    )

    # — Champs de rafraîchissement dynamique —
    stock_availability_info = fields.Char(string='Disponibilité Stock (Réel)', compute='_compute_stock_availability')
    stock_availability_color = fields.Selection([
        ('success', 'Disponible'),
        ('warning', 'Partiel'),
        ('danger', 'Manquant'),
    ], string='Couleur Stock', compute='_compute_stock_availability')

    @api.depends('line_ids', 'line_ids.plat_id', 'entree_plat_id', 'resistance_plat_id', 'dessert_plat_id')
    def _compute_display_menu(self):
        for order in self:
            parts = []
            if order.line_ids:
                # Trier pour respecter l'ordre logique : Entrée -> Plat -> Dessert
                sorted_lines = order.line_ids.sorted(key=lambda l: (
                    0 if 'entr' in (l.plat_type_id.name or '').lower() else 
                    1 if ('sist' in (l.plat_type_id.name or '').lower() or 'principal' in (l.plat_type_id.name or '').lower()) else 
                    2
                ))
                for line in sorted_lines:
                    parts.append(line.plat_id.display_name_website)

            else:
                # Fallback pour les anciennes commandes
                if order.entree_plat_id: parts.append(order.entree_plat_id.display_name_website)
                if order.resistance_plat_id: parts.append(order.resistance_plat_id.display_name_website)
                if order.dessert_plat_id: parts.append(order.dessert_plat_id.display_name_website)

            
            order.display_menu = " + ".join(parts) if parts else _("Menu personnalisé")


    @api.depends('line_ids.plat_id', 'quantity')
    def _compute_stock_availability(self):
        for rec in self:
            # Pour les nouveaux enregistrements sans lignes, pas de vérification possible
            if not rec.line_ids:
                rec.stock_availability_info = _("Aucun plat sélectionné")
                rec.stock_availability_color = 'success'
                continue

            try:
                check = rec._check_stock_availability()
                if check['sufficient']:
                    rec.stock_availability_info = _("Tout est en stock")
                    rec.stock_availability_color = 'success'
                elif check['can_proceed']:
                    rec.stock_availability_info = _("Certains ingrédients manquent")
                    rec.stock_availability_color = 'warning'
                else:
                    rec.stock_availability_info = _("Rupture de stock détectée")
                    rec.stock_availability_color = 'danger'
            except Exception:
                rec.stock_availability_info = _("Vérification en cours…")
                rec.stock_availability_color = 'success'

    @api.onchange('entree_plat_id', 'resistance_plat_id', 'dessert_plat_id', 'quantity')
    def _onchange_plats_stock_check(self):
        """Déclenche une notification si le stock devient insuffisant lors de la saisie."""
        self._compute_stock_availability()
        if self.stock_availability_color in ('warning', 'danger'):
            return {
                'warning': {
                    'title': _('Alerte Stock'),
                    'message': self.stock_availability_info + _(". Veuillez vérifier avant de confirmer.")
                }
            }

    facturation_state = fields.Selection([
        ('not_invoiced', 'Non facturée'),
        ('to_invoice',   'À facturer'),
        ('invoiced',     'Facturée'),
    ], string='État facturation', default='not_invoiced', required=True, tracking=True)


    @api.constrains('line_ids')
    def _check_lines_quota(self):
        for rec in self:
            # On vérifie le type de plat via is_plat_resistance (calculé sur lagunes.plat)
            resistance_count = len(rec.line_ids.filtered(lambda l: l.plat_id.is_plat_resistance))
            extra_count = len(rec.line_ids.filtered(lambda l: not l.plat_id.is_plat_resistance))
            
            if resistance_count > 1:
                raise ValidationError(_("Vous ne pouvez choisir qu'un seul plat de résistance."))
            if extra_count > 2:
                raise ValidationError(_("Vous ne pouvez choisir que 2 accompagnements (Entrée/Dessert) maximum."))
            if resistance_count == 0 and extra_count == 0:
                raise ValidationError(_("Veuillez sélectionner au moins un plat."))


    # Prix individuels par type (pour information)
    entree_prix = fields.Float(
        string='Prix entrée',
        related='entree_plat_id.prix_unitaire',
        store=True,
        readonly=True,
    )
    
    resistance_prix = fields.Float(
        string='Prix plat principal',
        related='resistance_plat_id.prix_unitaire',
        store=True,
        readonly=True,
    )
    
    dessert_prix = fields.Float(
        string='Prix dessert',
        related='dessert_plat_id.prix_unitaire',
        store=True,
        readonly=True,
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Commande de vente',
        readonly=True,
        copy=False,
    )

    create_date = fields.Datetime(string='Date de création', readonly=True)
    create_uid = fields.Many2one('res.users', string='Créé par', readonly=True)
    
    # HISTORIQUE ET STATUT
    state_history = fields.Html(
        string='Historique des statuts',
        readonly=True,
        help='Historique des changements de statut'
    )

    # ------------------------------------------------------------------ #
    #  COMPUTE                                                             #
    # ------------------------------------------------------------------ #

    @api.depends('date')
    def _compute_day_from_date(self):
        mapping = {5: '0', 6: '1', 0: '2', 1: '3', 2: '4', 3: '5', 4: '6'}
        for commande in self:
            if commande.date:
                commande.day = mapping.get(commande.date.weekday(), '2')
            else:
                commande.day = '2'

    @api.depends('quantity', 'option_ids', 'option_ids.prix_supplementaire', 'line_ids.price_subtotal')
    def _compute_prix_total(self):
        for commande in self:
            if commande.line_ids:
                # Nouvelle architecture : somme des sous-totaux des lignes
                prix_base = sum(commande.line_ids.mapped('price_subtotal'))
            else:
                # Fallback architecture classique (compatibilité historique)
                prix_plats = 0.0
                if commande.entree_plat_id:
                    prix_plats += commande.entree_plat_id.prix_unitaire
                if commande.resistance_plat_id:
                    prix_plats += commande.resistance_plat_id.prix_unitaire
                if commande.dessert_plat_id:
                    prix_plats += commande.dessert_plat_id.prix_unitaire
                prix_base = commande.quantity * prix_plats
            
            prix_options = sum(commande.option_ids.mapped('prix_supplementaire'))
            commande.prix_total = prix_base + (prix_options * commande.quantity)


    # ------------------------------------------------------------------ #
    #  CRUD                                                                #
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = (
                    self.env['ir.sequence'].next_by_code('lagunes.commande')
                    or _('Nouveau')
                )
        return super().create(vals_list)

    def write(self, vals):
        """
        FIX #8 — Protège les champs financiers des commandes
        qui sont en cours de facturation ou déjà facturées.
        """
        champs_proteges = {'quantity', 'entree_plat_id', 'resistance_plat_id', 'dessert_plat_id'}
        if champs_proteges & set(vals.keys()):
            for commande in self:
                if commande.facturation_state in ('to_invoice', 'invoiced'):
                    raise ValidationError(
                        _('La commande %(ref)s est en cours de facturation '
                          'ou déjà facturée et ne peut plus être modifiée '
                          '(plat, quantité).\n'
                          'Annulez d\'abord la période de facturation associée.')
                        % {'ref': commande.reference}
                    )
        return super().write(vals)

    # ------------------------------------------------------------------ #
    #  CONTRAINTES                                                         #
    # ------------------------------------------------------------------ #

    @api.constrains('quantity')
    def _check_quantity(self):
        for commande in self:
            if commande.quantity != 1:
                raise ValidationError(
                    _('La quantité par commande est limitée à 1 portion.')
                )

    @api.constrains('entreprise_id', 'date')
    def _check_max_orders_per_day(self):
        for record in self:
            if not record.entreprise_id or not record.date:
                continue
            max_orders = record.entreprise_id.max_orders_per_day
            if max_orders <= 0:
                continue
            count = self.search_count([
                ('id', '!=', record.id),
                ('entreprise_id', '=', record.entreprise_id.id),
                ('date', '=', record.date),
                ('state', '!=', 'cancelled'),
            ])
            if count >= max_orders:
                raise ValidationError(
                    _('Limite de %(max)d commande(s) par jour atteinte '
                      'pour %(name)s.\n%(count)d commande(s) déjà passée(s) aujourd\'hui.')
                    % {
                        'max': max_orders,
                        'name': record.entreprise_id.name,
                        'count': count,
                    }
                )

    # ------------------------------------------------------------------ #
    #  ONCHANGE                                                            #
    # ------------------------------------------------------------------ #

    # ================================================================ #
    #  ACTIONS - MODIFICATION GROUPÉE ET INTÉGRATION MARCHÉ             #
    # ================================================================ #
    
    def action_bulk_state_change(self, new_state):
        """Changer le statut de plusieurs commandes à la fois"""
        state_labels = dict(self._fields['state']._description_selection(self.env))
        
        for commande in self:
            old_state = commande.state
            commande.state = new_state
            
            # Enregistrer l'historique
            history_entry = f"<p><strong>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</strong> : "
            history_entry += f"Passage de <strong>{state_labels.get(old_state, old_state)}</strong> à "
            history_entry += f"<strong>{state_labels.get(new_state, new_state)}</strong> par {self.env.user.name}</p>"
            
            if commande.state_history:
                commande.state_history += history_entry
            else:
                commande.state_history = history_entry
            
            # INTÉGRATION MARCHÉ : Déduire les ingrédients du stock
            if new_state == 'preparing':
                commande._deduct_ingredients_from_market()
    
    def _check_stock_availability(self):
        """Vérifie la disponibilité du stock pour tous les ingrédients de la commande.

        Returns:
            dict: {
                'sufficient': True/False,
                'missing_lines': [
                    {
                        'article_id': id,
                        'article_name': str,
                        'requested': float,
                        'available': float,
                        'missing': float,
                        'unit': str,
                    },
                    ...
                ],
                'can_proceed': True/False,  # True si tous les articles ont stock > 0
            }
        """
        self.ensure_one()
        missing_lines = []
        can_proceed = True

        # Liste des plats à traiter
        plats = self.line_ids.mapped('plat_id')
        if not plats:
            # Fallback compatibilité (si créé manuellement sans lignes)
            if self.entree_plat_id: plats |= self.entree_plat_id
            if self.resistance_plat_id: plats |= self.resistance_plat_id
            if self.dessert_plat_id: plats |= self.dessert_plat_id


        for plat in plats:
            if not plat.ingredient_ids:
                continue

            for ingredient in plat.ingredient_ids:
                if not ingredient.is_quantifiable:
                    continue

                # Calculer quantité nécessaire
                quantity_raw = ingredient.quantity * self.quantity
                quantity_needed = ingredient.unit_id.compute_quantity(
                    quantity_raw,
                    ingredient.market_article_id.default_uom_id
                )

                # Vérifier stock disponible
                stock = self.env['lagunes.market.stock'].search([
                    ('article_id', '=', ingredient.market_article_id.id),
                    ('company_id', '=', self.company_id.id),
                ], limit=1)

                available_qty = stock.qty if stock else 0.0
                missing_qty = max(0.0, quantity_needed - available_qty)

                if missing_qty > 0:
                    missing_lines.append({
                        'article_id': ingredient.market_article_id.id,
                        'article_name': ingredient.market_article_id.name,
                        'requested': quantity_needed,
                        'available': available_qty,
                        'missing': missing_qty,
                        'unit': ingredient.market_article_id.default_uom or '',
                    })
                    if available_qty == 0:
                        can_proceed = False  # Stock totalement épuisé

        return {
            'sufficient': len(missing_lines) == 0,
            'missing_lines': missing_lines,
            'can_proceed': can_proceed,
        }

    def _deduct_ingredients_from_market(self, allow_insufficient=False, forced=False):
        """Déduire automatiquement les ingrédients du stock du marché pour les 3 plats du menu complet.

        Args:
            allow_insufficient: Si True, autorise déduction partielle si stock insuffisant
            forced: Si True, indique que c'est un forçage utilisateur (log pour audit)

        Returns:
            dict: Résultat de l'opération avec détails
        """
        results = []

        for commande in self:
            # ═════════════════════════════════════════════════════════════════
            # VÉRIFICATION IDEMPOTENCE
            # ═════════════════════════════════════════════════════════════════
            if commande.is_stock_deducted:
                _logger.info(_('Stock déjà déduit pour commande %s, on skip'), commande.reference)
                continue

            # Verrouillage ligne commande pour éviter double déduction concurrence
            self.env.cr.execute(
                "SELECT is_stock_deducted FROM lagunes_commande WHERE id = %s FOR UPDATE",
                (commande.id,)
            )
            row = self.env.cr.fetchone()
            if row and row[0]:
                continue  # Re-vérification après verrou

            # ═════════════════════════════════════════════════════════════════
            # PRÉPARATION DES DONNÉES
            # ═════════════════════════════════════════════════════════════════
            plats = commande.line_ids.mapped('plat_id')
            if not plats:
                if commande.entree_plat_id: plats |= commande.entree_plat_id
                if commande.resistance_plat_id: plats |= commande.resistance_plat_id
                if commande.dessert_plat_id: plats |= commande.dessert_plat_id


            any_capped = False
            deduction_details = []

            # ═════════════════════════════════════════════════════════════════
            # DÉDUCTION STOCK
            # ═════════════════════════════════════════════════════════════════
            for plat in plats:
                if not plat.ingredient_ids:
                    continue

                for ingredient in plat.ingredient_ids:
                    if not ingredient.is_quantifiable:
                        continue

                    # Calcul quantité à déduire
                    quantity_raw = ingredient.quantity * commande.quantity
                    quantity_to_deduct = ingredient.unit_id.compute_quantity(
                        quantity_raw,
                        ingredient.market_article_id.default_uom_id
                    )

                    # Préparer note traçable
                    note = _('Déduction auto : %s (Cmd %s - %s le %s)') % (
                        plat.name,
                        commande.reference,
                        commande.entreprise_id.name,
                        commande.date.strftime('%d/%m/%Y') if commande.date else ''
                    )

                    if forced:
                        note += _(' [FORÇÉ par %s]') % commande.stock_forced_by_id.name

                    # Appel méthode sécurisée avec protection
                    result = self.env['lagunes.market.stock'].with_company(
                        commande.company_id
                    )._remove_quantity(
                        article_id=ingredient.market_article_id.id,
                        qty=quantity_to_deduct,
                        note=note,
                        reference=commande.reference,
                        market_id=commande.week_menu_id.id if commande.week_menu_id else False,
                        created_by=self.env.user.id,
                        move_category='order_deduction',
                        allow_capped=allow_insufficient,
                        plat_name=plat.display_name_website or plat.name,
                        source='cantine',
                    )

                    if result['is_capped']:
                        any_capped = True

                    deduction_details.append({
                        'article': ingredient.market_article_id.name,
                        'requested': result['requested_qty'],
                        'actual': result['actual_qty'],
                        'is_capped': result['is_capped'],
                    })

            # ═════════════════════════════════════════════════════════════════
            # MISE À JOUR ÉTAT COMMANDE
            # ═════════════════════════════════════════════════════════════════
            now = fields.Datetime.now()
            commande.write({
                'is_stock_deducted': True,
                'stock_deduction_date': now,
                'stock_insufficient': any_capped,
            })

            results.append({
                'commande_id': commande.id,
                'reference': commande.reference,
                'success': True,
                'any_capped': any_capped,
                'details': deduction_details,
            })

        return results
    
    def get_commande_history(self):
        """Afficher l'historique complet des commandes"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Historique des commandes',
            'res_model': 'lagunes.commande',
            'view_mode': 'list,form',
            'domain': [('entreprise_id', '=', self.entreprise_id.id)],
            'context': {'search_default_by_date': 1},
        }


    # ------------------------------------------------------------------ #
    #  ACTIONS ÉTAT                                                        #
    # ------------------------------------------------------------------ #

    def action_confirm(self):
        for commande in self:
            commande.state = 'confirmed'

    def action_prepare(self):
        """Passer en préparation avec vérification stock préalable"""
        self.ensure_one()

        # Vérifier si stock déjà déduit (idempotence)
        if self.is_stock_deducted:
            # Stock déjà déduit, juste changer le statut
            self.state = 'preparing'
            return True

        # Vérifier disponibilité stock
        stock_check = self._check_stock_availability()

        if stock_check['sufficient']:
            # Stock suffisant, déduction normale
            self._deduct_ingredients_from_market()
            self.state = 'preparing'
            return True
        else:
            # Stock insuffisant, ouvrir wizard warning
            return self._open_stock_warning_wizard(stock_check, 'preparing')

    def _open_stock_warning_wizard(self, stock_check, target_state):
        """Ouvre le wizard d'avertissement stock insuffisant"""
        self.ensure_one()

        # Créer le wizard
        wizard = self.env['lagunes.stock.insufficient.warning'].create({
            'new_state': target_state,
        })

        # Lier les commandes (juste celle-ci pour action individuelle)
        wizard.commande_ids = [(6, 0, [self.id])]

        # Créer les lignes de détail
        for line_data in stock_check['missing_lines']:
            self.env['lagunes.stock.warning.line'].create({
                'warning_id': wizard.id,
                'article_id': line_data['article_id'],
                'requested_qty': line_data['requested'],
                'available_qty': line_data['available'],
                'missing_qty': line_data['missing'],
                'unit': line_data['unit'],
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('⚠️ Stock insuffisant'),
            'res_model': 'lagunes.stock.insufficient.warning',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }

    def action_ready(self):
        for commande in self:
            commande.state = 'ready'

    def action_deliver(self):
        """Livrer la commande avec vérification stock insuffisant"""
        for commande in self:
            # Bloquer livraison si stock insuffisant non résolu
            if commande.stock_insufficient:
                # Seul admin peut forcer la livraison
                if not self.env.user.has_group('base.group_system'):
                    raise ValidationError(_(
                        "Commande %(ref)s : Impossible de livrer car le stock était insuffisant "
                        "lors de la préparation.\n\n"
                        "Forçage par : %(user)s le %(date)s\n"
                        "Veuillez contacter un administrateur pour valider cette livraison."
                    ) % {
                        'ref': commande.reference,
                        'user': commande.stock_forced_by_id.name or _('Inconnu'),
                        'date': commande.stock_forced_date.strftime('%d/%m/%Y %H:%M') if commande.stock_forced_date else _('Inconnue'),
                    })
                else:
                    # Log admin forcing
                    commande.message_post(
                        body=_("<strong>⚠️ Livraison forcée par administrateur</strong><br/>"
                               "Stock était marqué insuffisant.<br/>"
                               "Livraison validée par : %s") % self.env.user.name,
                        subtype_xmlid='mail.mt_note',
                    )

            commande.state = 'delivered'

    def action_cancel(self):
        for commande in self:
            commande.state = 'cancelled'
            # Restaurer le stock (rollback)
            commande._restore_ingredients_to_market()
    
    def _restore_ingredients_to_market(self):
        """Restaure automatiquement les ingrédients au stock du marché lors de l'annulation.

        Ne restaure que si le stock avait été déduit (idempotence).
        """
        for commande in self:
            # Ne restaurer que si stock avait été déduit
            if not commande.is_stock_deducted:
                _logger.info(_('Pas de restauration nécessaire pour %s (stock non déduit)'), commande.reference)
                continue

            # Liste des plats à traiter
            plats = []
            if commande.entree_plat_id:
                plats.append(commande.entree_plat_id)
            if commande.resistance_plat_id:
                plats.append(commande.resistance_plat_id)
            if commande.dessert_plat_id:
                plats.append(commande.dessert_plat_id)

            for plat in plats:
                if not plat.ingredient_ids:
                    continue

                for ingredient in plat.ingredient_ids:
                    if not ingredient.is_quantifiable:
                        continue

                    # Calcul quantité à restaurer
                    quantity_raw = ingredient.quantity * commande.quantity
                    quantity_to_restore = ingredient.unit_id.compute_quantity(
                        quantity_raw,
                        ingredient.market_article_id.default_uom_id
                    )

                    # Note avec contexte restauration
                    note = _('Restockage (annulation cmd %s): %s - %s') % (
                        commande.reference,
                        plat.name,
                        commande.entreprise_id.name,
                    )

                    # Restauration via méthode enrichie
                    self.env['lagunes.market.stock'].with_company(commande.company_id)._add_quantity(
                        article_id=ingredient.market_article_id.id,
                        qty=quantity_to_restore,
                        note=note,
                        reference=commande.reference,
                        market_id=commande.week_menu_id.id if commande.week_menu_id else False,
                        created_by=self.env.user.id,
                        move_category='order_deduction',  # Même catégorie, c'est un rollback
                        plat_name=plat.display_name_website or plat.name,
                        source='cantine',
                    )

            # Reset marqueurs (mais garder trace dans historique)
            commande.write({
                'is_stock_deducted': False,
                'stock_insufficient': False,
            })

    # ------------------------------------------------------------------ #
    #  FACTURATION UNITAIRE (legacy)                                       #
    # ------------------------------------------------------------------ #

    def create_sale_order(self):
        """Création d'une commande de vente individuelle (facturation unitaire)."""
        self.ensure_one()

        if self.sale_order_id:
            raise ValidationError(
                _('Une commande de vente existe déjà pour cette commande.')
            )

        # Déterminer le produit à utiliser (résistance prioritaire, puis entrée, puis dessert)
        main_plat = self.resistance_plat_id or self.entree_plat_id or self.dessert_plat_id
        if not main_plat or not main_plat.product_id:
            raise ValidationError(_('Aucun plat valide trouvé pour créer la commande de vente.'))

        sale_order = self.env['sale.order'].create({
            'partner_id': self.entreprise_id.id,
            'date_order': datetime.now(),
            'order_line': [(0, 0, {
                'product_id': main_plat.product_id.id,
                'name': self._get_order_line_description(),
                'product_uom_qty': self.quantity,
                'price_unit': self.prix_total,
                'tax_id': [(5, 0, 0)],
            })],
        })

        self.sale_order_id = sale_order.id
        self.facturation_state = 'to_invoice'

        return {
            'type': 'ir.actions.act_window',
            'name': _('Commande de vente'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------ #
    #  HELPERS                                                             #
    # ------------------------------------------------------------------ #

    def _get_order_line_description(self):
        # Construire la description avec toutes les lignes
        description_parts = []
        for line in self.line_ids:
            type_label = _("Plat")
            if 'entr' in line.plat_type_id.name.lower():
                type_label = _("Entrée")
            elif 'dessert' in line.plat_type_id.name.lower():
                type_label = _("Dessert")
            
            description_parts.append(f"{type_label}: {line.plat_id.display_name_website}")
        
        description = ' + '.join(description_parts) if description_parts else _('Menu personnalisé')
        
        options = self.option_ids.mapped('name')
        if options:
            description += f" ({', '.join(options)})"
        if self.notes:
            description += f"\n{_('Notes')} : {self.notes}"
        return description


    def get_options_display(self):
        self.ensure_one()
        options = self.option_ids.mapped('name')
        return ', '.join(options) if options else _('Aucune')
