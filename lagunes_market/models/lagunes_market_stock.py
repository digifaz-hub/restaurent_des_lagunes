# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo import _


class LagunesMarketStock(models.Model):
    """État actuel du stock pour chaque article du marché.
    Une seule ligne par article par société.
    """
    _name = 'lagunes.market.stock'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Stock du marché'
    _order = 'qty desc'
    _rec_name = 'article_id'

    article_id = fields.Many2one(
        comodel_name='lagunes.market.article',
        string='Article',
        required=True,
        ondelete='cascade',
    )
    category_id = fields.Many2one(
        comodel_name='lagunes.market.article.category',
        string='Catégorie',
        related='article_id.category_id',
        store=True,
    )
    qty = fields.Float(
        string='Quantité en stock',
        default=0.0,
        required=True,
        tracking=True,
        digits=(16, 3),
    )
    # Utilise le champ texte calculé default_uom (computed depuis default_uom_id)
    uom = fields.Char(
        string='Unité',
        related='article_id.default_uom',
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )

    # ═══════════════════════════════════════════════════════════════════════
    # GESTION STOCK MINIMUM ET ALERTES
    # ═══════════════════════════════════════════════════════════════════════

    reorder_point = fields.Float(
        string='Stock minimum',
        default=0.0,
        help='Seuil de réapprovisionnement. Alerte quand stock ≤ cette valeur',
        tracking=True,
    )

    reorder_quantity = fields.Float(
        string='Qté de réappro. suggérée',
        default=0.0,
        help='Quantité suggérée lors du réapprovisionnement',
    )

    stock_status = fields.Selection([
        ('ok', 'OK'),
        ('low', 'Faible'),
        ('critical', 'Critique'),
    ], string='État stock', compute='_compute_stock_status', store=True)

    is_low_stock = fields.Boolean(
        string='Stock faible',
        compute='_compute_stock_status',
        store=True,
    )

    is_critical = fields.Boolean(
        string='Stock critique',
        compute='_compute_stock_status',
        store=True,
    )

    alert_sent = fields.Boolean(
        string='Alerte envoyée',
        default=False,
        help='Marqueur technique : True si alerte déjà envoyée pour ce stock',
    )

    last_movement_date = fields.Date(
        string='Dernier mouvement',
        compute='_compute_last_movement_date',
        store=False,
    )

    autonomy_days = fields.Integer(
        string='Autonomie (Jours)',
        compute='_compute_autonomy_days',
        help='Nombre de jours restants avant rupture, basé sur la consommation des 30 derniers jours.',
    )

    @api.depends('qty', 'reorder_point')
    def _compute_stock_status(self):
        """Calcule l'état du stock en fonction des seuils."""
        for stock in self:
            if stock.qty <= 0:
                stock.stock_status = 'critical'
                stock.is_critical = True
                stock.is_low_stock = True
            elif stock.reorder_point > 0 and stock.qty <= stock.reorder_point:
                stock.stock_status = 'low'
                stock.is_low_stock = True
                stock.is_critical = False
            else:
                stock.stock_status = 'ok'
                stock.is_low_stock = False
                stock.is_critical = False
            # Reset alert flag when stock returns to OK
            if stock.stock_status == 'ok' and stock.alert_sent:
                stock.alert_sent = False

    def _compute_last_movement_date(self):
        """Récupère la date du dernier mouvement de stock."""
        for stock in self:
            last_move = self.env['lagunes.market.stock.move'].search([
                ('article_id', '=', stock.article_id.id),
                ('company_id', '=', stock.company_id.id),
            ], order='date desc, id desc', limit=1)
            stock.last_movement_date = last_move.date if last_move else False

    def _compute_autonomy_days(self):
        """Calcule l'autonomie en jours basée sur la conso des 30 derniers jours."""
        today = fields.Date.today()
        from datetime import timedelta
        date_limit = today - timedelta(days=30)
        for stock in self:
            if stock.qty <= 0:
                stock.autonomy_days = 0
                continue
            
            # Somme des sorties sur 30 jours
            moves = self.env['lagunes.market.stock.move'].search([
                ('article_id', '=', stock.article_id.id),
                ('company_id', '=', stock.company_id.id),
                ('move_type', '=', 'out'),
                ('date', '>=', date_limit)
            ])
            total_out = sum(moves.mapped('qty'))
            daily_avg = total_out / 30.0 if total_out > 0 else 0
            
            if daily_avg > 0:
                stock.autonomy_days = int(stock.qty / daily_avg)
            else:
                stock.autonomy_days = 999 # Autonomie infinie si pas de conso

    _sql_constraints = [
        ('article_company_uniq', 'unique(article_id, company_id)',
         'Un seul stock par article et par société.'),
    ]

    def _add_quantity(self, article_id, qty, note=False, market_id=False,
                      reference=False, created_by=False, move_category=False,
                      plat_name=False, source=False):
        """Ajoute une quantité au stock avec verrou exclusif et trace le mouvement.

        Args:
            article_id: ID de l'article
            qty: Quantité à ajouter (doit être > 0)
            note: Description du mouvement
            market_id: ID du marché source (optionnel)
            reference: Référence externe (ex: numéro commande)
            created_by: ID de l'utilisateur créant le mouvement
            move_category: Catégorie du mouvement (purchase, order_deduction, etc.)
            plat_name: Nom du plat cantine ayant provoqué le mouvement (optionnel)
            source: 'cantine' ou 'traiteur' (optionnel)

        Returns:
            True si succès
        """
        if qty <= 0:
            raise ValueError(_("La quantité à ajouter doit être positive"))

        # Verrouillage exclusif pour éviter les conflits de concurrence
        self.env.cr.execute(
            "SELECT id, qty FROM lagunes_market_stock WHERE article_id = %s AND company_id = %s FOR UPDATE",
            (article_id, self.env.company.id)
        )
        row = self.env.cr.fetchone()

        if row:
            self.env.cr.execute(
                "UPDATE lagunes_market_stock SET qty = qty + %s WHERE article_id = %s AND company_id = %s",
                (qty, article_id, self.env.company.id)
            )
            self.env['lagunes.market.stock'].invalidate_model(['qty'])
        else:
            self.create({
                'article_id': article_id,
                'qty': qty,
                'company_id': self.env.company.id,
            })

        # Création du mouvement de stock enrichi
        move_vals = {
            'article_id': article_id,
            'qty': qty,
            'move_type': 'in',
            'market_id': market_id,
            'date': fields.Date.context_today(self),
            'note': note or _('Entrée manuelle'),
            'reference': reference,
            'move_category': move_category or 'other',
            'plat_name': plat_name or False,
            'source': source or False,
        }
        if created_by:
            move_vals['created_by'] = created_by

        self.env['lagunes.market.stock.move'].create(move_vals)
        return True

    def _remove_quantity(self, article_id, qty, note=False, market_id=False,
                         reference=False, created_by=False, move_category=False,
                         allow_capped=False, plat_name=False, source=False):
        """Retire une quantité du stock (sécurisé) et trace le mouvement.

        Args:
            article_id: ID de l'article
            qty: Quantité à retirer (doit être > 0)
            note: Description du mouvement
            market_id: ID du marché source (optionnel)
            reference: Référence externe (ex: numéro commande)
            created_by: ID de l'utilisateur créant le mouvement
            move_category: Catégorie du mouvement
            allow_capped: Si True, autorise retrait partiel si stock insuffisant
                         (retourne la quantité effectivement retirée)
            plat_name: Nom du plat cantine ayant provoqué le mouvement (optionnel)
            source: 'cantine' ou 'traiteur' (optionnel)

        Returns:
            dict: {
                'success': True/False,
                'requested_qty': qty demandée,
                'actual_qty': qty effectivement retirée,
                'is_capped': True si stock insuffisant,
                'available_qty': qty disponible avant retrait
            }
        """
        if qty <= 0:
            raise ValueError(_("La quantité à retirer doit être positive"))

        # Verrouillage exclusif pour éviter les conflits de concurrence
        self.env.cr.execute(
            "SELECT id, qty FROM lagunes_market_stock WHERE article_id = %s AND company_id = %s FOR UPDATE",
            (article_id, self.env.company.id)
        )
        row = self.env.cr.fetchone()

        if row:
            current_qty = row[1]
            is_capped = current_qty < qty

            # Protection contre stock négatif : min 0
            if is_capped and not allow_capped:
                # Stock insuffisant et non autorisé à capper
                return {
                    'success': False,
                    'requested_qty': qty,
                    'actual_qty': 0,
                    'is_capped': True,
                    'available_qty': current_qty,
                }

            # Calcul quantité effective (jamais négative)
            actual_qty = min(qty, current_qty)
            new_qty = current_qty - actual_qty

            self.env.cr.execute(
                "UPDATE lagunes_market_stock SET qty = %s WHERE article_id = %s AND company_id = %s",
                (new_qty, article_id, self.env.company.id)
            )
            self.env['lagunes.market.stock'].invalidate_model(['qty'])

            # Création du mouvement de stock enrichi
            move_vals = {
                'article_id': article_id,
                'qty': actual_qty,  # Quantité réellement retirée
                'move_type': 'out',
                'market_id': market_id,
                'date': fields.Date.context_today(self),
                'note': note or _('Sortie manuelle'),
                'reference': reference,
                'move_category': move_category or 'other',
                'plat_name': plat_name or False,
                'source': source or False,
            }
            if created_by:
                move_vals['created_by'] = created_by

            self.env['lagunes.market.stock.move'].create(move_vals)

            # Déclencher alerte si stock faible après mouvement
            if new_qty >= 0:
                self._trigger_low_stock_alert(article_id, new_qty)

            return {
                'success': True,
                'requested_qty': qty,
                'actual_qty': actual_qty,
                'is_capped': is_capped,
                'available_qty': current_qty,
            }

        # Pas de stock trouvé
        return {
            'success': False,
            'requested_qty': qty,
            'actual_qty': 0,
            'is_capped': True,
            'available_qty': 0.0,
        }

    def _trigger_low_stock_alert(self, article_id, current_qty):
        """Déclenche une notification si le stock passe sous le seuil critique."""
        stock = self.search([
            ('article_id', '=', article_id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not stock or stock.alert_sent:
            return

        if stock.is_low_stock or stock.is_critical:
            # Envoyer notification Odoo (bus)
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'lagunes.market.low_stock',
                {
                    'article_id': stock.article_id.id,
                    'article_name': stock.article_id.name,
                    'current_qty': current_qty,
                    'reorder_point': stock.reorder_point,
                    'status': stock.stock_status,
                }
            )
            stock.alert_sent = True

    def action_manual_adjustment(self, qty_delta, reason):
        """Ajustement manuel du stock avec traçabilité complète.

        Args:
            qty_delta: Quantité à ajouter (positif) ou retirer (négatif)
            reason: Justification obligatoire de l'ajustement
        """
        self.ensure_one()

        if not reason or len(reason.strip()) < 5:
            raise ValidationError(_("Une justification d'au moins 5 caractères est obligatoire."))

        if qty_delta == 0:
            raise ValidationError(_("La quantité d'ajustement ne peut pas être nulle."))

        # Déterminer type de mouvement
        if qty_delta > 0:
            self._add_quantity(
                article_id=self.article_id.id,
                qty=qty_delta,
                note=_('Ajustement manuel : %s') % reason,
                reference=_('AJUST-%s') % self.env.user.login,
                created_by=self.env.user.id,
                move_category='adjustment',
            )
        else:
            self._remove_quantity(
                article_id=self.article_id.id,
                qty=abs(qty_delta),
                note=_('Ajustement manuel : %s') % reason,
                reference=_('AJUST-%s') % self.env.user.login,
                created_by=self.env.user.id,
                move_category='adjustment',
                allow_capped=True,  # Autoriser ajustement même si stock insuffisant
            )

        # Logger dans le chatter
        self.message_post(
            body=_("<strong>Ajustement manuel du stock</strong><br/>"
                   "Quantité : %s<br/>"
                   "Nouveau stock : %s %s<br/>"
                   "Justification : %s<br/>"
                   "Par : %s") % (
                qty_delta,
                self.qty,
                self.uom,
                reason,
                self.env.user.name,
            ),
            subtype_xmlid='mail.mt_note',
        )

    def action_open_adjustment_wizard(self):
        self.ensure_one()
        return {
            'name': _('Ajustement manuel'),
            'type': 'ir.actions.act_window',
            'res_model': 'lagunes.market.adjustment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_stock_id': self.id,
            }
        }

class LagunesMarketStockMove(models.Model):
    """Historique des mouvements de stock."""
    _name = 'lagunes.market.stock.move'
    _description = 'Mouvement de stock des articles de marché'
    _order = 'date desc, id desc'

    article_id = fields.Many2one(
        comodel_name='lagunes.market.article',
        string='Article',
        required=True,
        ondelete='restrict',
    )
    category_id = fields.Many2one(
        comodel_name='lagunes.market.article.category',
        string='Catégorie',
        related='article_id.category_id',
        store=True,
    )
    qty = fields.Float(
        string='Quantité',
        required=True,
        digits=(16, 3),
    )
    move_type = fields.Selection(
        selection=[
            ('in', 'Entrée'),
            ('out', 'Sortie'),
        ],
        string='Type',
        required=True,
        default='in',
    )
    market_id = fields.Many2one(
        comodel_name='lagunes.market',
        string='Marché source',
        ondelete='set null',
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
    )
    note = fields.Char(string='Note')
    uom = fields.Char(
        string='Unité',
        related='article_id.default_uom',
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )

    # ═══════════════════════════════════════════════════════════════════════
    # CHAMPS ENRICHIS POUR TRACABILITÉ COMPLÈTE
    # ═══════════════════════════════════════════════════════════════════════

    reference = fields.Char(
        string='Référence',
        help='Référence externe (ex: numéro de commande, facture)',
        index=True,
    )

    created_by = fields.Many2one(
        comodel_name='res.users',
        string='Créé par',
        default=lambda self: self.env.user,
        readonly=True,
    )

    move_category = fields.Selection([
        ('purchase', 'Achat au marché'),
        ('order_deduction', 'Déduction commande cantine'),
        ('adjustment', 'Ajustement manuel'),
        ('waste', 'Perte/Déchet'),
        ('inventory_adjustment', 'Ajustement d\'inventaire'),
        ('leftover', 'Stock initial de marché'),
        ('other', 'Autre'),
    ], string='Catégorie de mouvement', default='other', required=True,
       help='Catégorie du mouvement pour une meilleure traçabilité')

    source = fields.Selection([
        ('cantine', 'Cantine'),
        ('traiteur', 'Traiteur'),
    ], string='Source', default=False, index=True,
       help='Origine de la déduction (Cantine ou Traiteur).')

    # Nom du plat cantine responsable de la consommation (Char pour éviter dépendance circulaire)
    plat_name = fields.Char(
        string='Plat (Cantine)',
        help='Nom du plat de la cantine ayant provoqué cette consommation d\'ingrédient.',
    )
