# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class LagunesMarket(models.Model):
    """Document principal représentant une sortie au marché d'approvisionnement."""
    _name = 'lagunes.market'
    _description = 'Marché d\'approvisionnement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name desc'

    # ─── Identification ────────────────────────────────────────────────────────
    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
        tracking=True,
    )
    date = fields.Date(
        string='Date du marché',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsable',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    # ─── Montant ────────────────────────────────────────────────────────────────
    amount_total = fields.Monetary(
        string='Montant total',
        currency_field='currency_id',
        compute='_compute_amount_total',
        store=True,
        readonly=True,
        tracking=True,
        help='Montant total calculé automatiquement (somme des sous-totaux des lignes)',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Devise',
        related='company_id.currency_id',
        readonly=True,
        store=True,
    )

    # ─── Statut ─────────────────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('validated', 'Validé'),
            ('cancelled', 'Annulé'),
        ],
        string='Statut',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )

    # ─── Lignes d'articles achetés ──────────────────────────────────────────────
    line_ids = fields.One2many(
        comodel_name='lagunes.market.line',
        inverse_name='market_id',
        string='Articles achetés',
        copy=True,
    )

    # ─── Reliquats du marché précédent ──────────────────────────────────────────
    leftover_ids = fields.One2many(
        comodel_name='lagunes.market.leftover',
        inverse_name='market_id',
        string='Reliquats du marché précédent',
        copy=False,
    )

    # ─── Notes ──────────────────────────────────────────────────────────────────
    notes = fields.Text(
        string='Notes / Observations',
        tracking=True,
    )

    # ─── Lien comptable ─────────────────────────────────────────────────────────
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Écriture comptable',
        readonly=True,
        copy=False,
    )
    move_count = fields.Integer(
        string='Nombre d\'écritures',
        compute='_compute_move_count',
    )

    def _compute_move_count(self):
        for record in self:
            record.move_count = 1 if record.move_id else 0

    @api.depends('line_ids.subtotal')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.line_ids.mapped('subtotal'))

    # ─── Verrouillage ──────────────────────────────────────────────────────────
    def write(self, vals):
        """Bloque la modification des champs critiques si le marché n'est plus en brouillon."""
        for record in self:
            if record.state != 'draft':
                # Liste des champs dont on interdit la modification hors brouillon
                # (sauf le champ 'state' lui-même qui est piloté par les boutons)
                # amount_total retiré car maintenant calculé automatiquement
                locked_fields = {'line_ids', 'leftover_ids', 'date', 'company_id'}
                if any(field in vals for field in locked_fields):
                    raise UserError(
                        _('Impossible de modifier un marché déjà %s. '
                          'Veuillez le remettre en brouillon pour toute modification.') %
                        dict(self._fields['state'].selection).get(record.state, record.state)
                    )
        return super().write(vals)

    # ─── Contraintes ────────────────────────────────────────────────────────────
    @api.constrains('date')
    def _check_date_future(self):
        for record in self:
            if record.date and record.date > fields.Date.context_today(record):
                raise ValidationError(_('La date du marché ne peut pas être dans le futur.'))


    # ─── Séquence ───────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'lagunes.market.sequence'
                ) or _('Nouveau')
            if not vals.get('date'):
                vals['date'] = fields.Date.context_today(self)
        return super().create(vals_list)

    # ─── Actions workflow ───────────────────────────────────────────────────────
    def action_validate(self):
        """Valide le marché : met à jour le stock et crée l'écriture comptable."""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(
                _('Ce marché a déjà été traité (statut : %s). '
                  'Impossible de le valider à nouveau.') % dict(
                    self._fields['state'].selection).get(self.state, self.state)
            )

        if not self.line_ids:
            raise UserError(
                _('Impossible de valider un marché sans article acheté. '
                  'Veuillez ajouter au moins un article avant de valider.')
            )

        if not self.amount_total or self.amount_total <= 0:
            raise UserError(
                _('Veuillez saisir un montant total valide avant de valider le marché.')
            )

        stock_model = self.env['lagunes.market.stock'].with_company(self.company_id)
        move_stock_model = self.env['lagunes.market.stock.move'].with_company(self.company_id)

        # Étape 1 : Reliquats → remise à zéro puis ajout qty_remaining
        for leftover in self.leftover_ids:
            if leftover.qty_remaining <= 0:
                continue
            self.env.cr.execute(
                "SELECT id FROM lagunes_market_stock WHERE article_id = %s AND company_id = %s FOR UPDATE",
                (leftover.article_id.id, self.company_id.id)
            )
            row = self.env.cr.fetchone()
            if row:
                self.env.cr.execute(
                    "UPDATE lagunes_market_stock SET qty = 0 WHERE article_id = %s AND company_id = %s",
                    (leftover.article_id.id, self.company_id.id)
                )
                stock_model.invalidate_model(['qty'])

            stock_model._add_quantity(
                article_id=leftover.article_id.id,
                qty=leftover.qty_remaining,
                note=_('Reliquat déclaré — marché %s') % self.name,
                market_id=self.id
            )

        # Étape 2 : Nouveaux achats
        for line in self.line_ids:
            # Snapshot du stock AVANT l'ajout — figé définitivement
            current_stock = stock_model.search(
                [('article_id', '=', line.article_id.id), ('company_id', '=', self.company_id.id)],
                limit=1,
            )
            line.write({'stock_before': current_stock.qty if current_stock else 0.0})

            stock_model._add_quantity(
                article_id=line.article_id.id,
                qty=line.qty,
                note=_('Entrée via marché %s') % self.name,
                market_id=self.id
            )

        # Écriture comptable
        self._create_accounting_move()

        # Passage en validé — le write déclenche le rechargement du statut en UI
        self.write({'state': 'validated'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marché validé'),
                'message': _('Le marché %s a été validé avec succès.') % self.name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_cancel(self):
        """Annule le marché avec rollback complet."""
        self.ensure_one()

        if self.state == 'cancelled':
            raise UserError(_('Ce marché est déjà annulé.'))

        if self.state == 'validated':
            stock_model = self.env['lagunes.market.stock'].with_company(self.company_id)
            move_stock_model = self.env['lagunes.market.stock.move'].with_company(self.company_id)

            for leftover in self.leftover_ids:
                if leftover.qty_remaining <= 0:
                    continue
                result = stock_model._remove_quantity(
                    article_id=leftover.article_id.id,
                    qty=leftover.qty_remaining,
                    note=_('Annulation reliquat — marché %s') % self.name,
                    market_id=self.id,
                    allow_capped=True,
                )
                if result.get('is_capped'):
                    self.message_post(body=_("Attention : Le stock de l'article '%s' était insuffisant lors de l'annulation du reliquat. Le stock a été remis à 0.") % leftover.article_id.name)

            for line in self.line_ids:
                result = stock_model._remove_quantity(
                    article_id=line.article_id.id,
                    qty=line.qty,
                    note=_('Annulation du marché %s') % self.name,
                    market_id=self.id,
                    allow_capped=True,
                )
                if result.get('is_capped'):
                    self.message_post(body=_("Attention : Le stock de l'article '%s' était insuffisant lors de l'annulation du marché. Le stock a été remis à 0.") % line.article_id.name)

            if self.move_id and self.move_id.state in ('posted', 'draft'):
                try:
                    if self.move_id.state == 'posted':
                        self.move_id.button_draft()
                    self.move_id.button_cancel()
                except Exception as e:
                    raise UserError(
                        _('Impossible d\'annuler l\'écriture comptable : %s\n'
                          'Veuillez l\'annuler manuellement depuis la comptabilité.') % str(e)
                    )

        self.write({'state': 'cancelled'})
        self.message_post(body=_('Marché annulé. Stock et écriture comptable remis à jour.'))

    def action_reset_draft(self):
        self.ensure_one()
        if self.state != 'cancelled':
            raise UserError(_('Seul un marché annulé peut être remis en brouillon.'))
        self.write({
            'state': 'draft',
            'move_id': False,
        })
        self.message_post(body=_('Marché remis en brouillon. Le lien avec l\'ancienne écriture comptable a été supprimé.'))

    # ─── Pré-remplir les reliquats ─────────────────────────────────────────────
    def action_prefill_leftovers(self):
        """Pré-remplit l'onglet Reliquats depuis le stock actuel,
        puis recharge le formulaire pour afficher les lignes créées.
        """
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Impossible de modifier un marché déjà validé ou annulé.'))

        # Supprime les reliquats existants
        self.leftover_ids.unlink()
 
        # On ne prend que les articles actifs avec du stock
        stocks = self.env['lagunes.market.stock'].search([
            ('qty', '>', 0),
            ('article_id.active', '=', True)
        ])
        leftovers = []
        for stock in stocks:
            leftovers.append({
                'market_id': self.id,
                'article_id': stock.article_id.id,
                'uom_id': stock.article_id.default_uom_id.id or False,
                'qty_remaining': stock.qty,
            })
        if leftovers:
            self.env['lagunes.market.leftover'].create(leftovers)

        # ── Retourne un rechargement du formulaire pour afficher les nouvelles lignes ──
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lagunes.market',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
            'context': {
                **self.env.context,
                'prefill_done': True,
                'default_tab': 'leftovers',
            },
        }

    # ─── Comptabilité ───────────────────────────────────────────────────────────
    def _get_accounting_config(self):
        IrParam = self.env['ir.config_parameter'].sudo()
        account_id_str = IrParam.get_param('lagunes_market.account_id')
        journal_id_str = IrParam.get_param('lagunes_market.journal_id')

        if not account_id_str or not journal_id_str:
            raise UserError(
                _('Les paramètres comptables du module "Gestion des marchés" ne sont pas configurés.\n'
                  'Veuillez aller dans Configuration → Paramètres comptables pour '
                  'définir le compte de dépense et le journal.')
            )

        account = self.env['account.account'].browse(int(account_id_str))
        journal = self.env['account.journal'].browse(int(journal_id_str))

        if not account.exists():
            raise UserError(
                _('Le compte de dépense marché configuré n\'existe plus. '
                  'Veuillez le reconfigurer dans les paramètres.')
            )
        if not journal.exists():
            raise UserError(
                _('Le journal de dépense marché configuré n\'existe plus. '
                  'Veuillez le reconfigurer dans les paramètres.')
            )
        return account, journal

    def _create_accounting_move(self):
        account, journal = self._get_accounting_config()

        if not journal.default_account_id:
            raise UserError(
                _('Le journal "%s" n\'a pas de compte de contrepartie par défaut. '
                  'Veuillez configurer ce compte dans la comptabilité.')
                % journal.name
            )

        counterpart_account = journal.default_account_id
        ref = _('Marché %s — %s') % (
            self.name,
            self.date.strftime('%d/%m/%Y') if self.date else '',
        )

        move_vals = {
            'journal_id': journal.id,
            'date': self.date or fields.Date.context_today(self),
            'ref': ref,
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'name': ref,
                    'debit': self.amount_total,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': counterpart_account.id,
                    'name': ref,
                    'debit': 0.0,
                    'credit': self.amount_total,
                }),
            ],
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.move_id = move

    # ─── Smart buttons ─────────────────────────────────────────────────────────
    def action_open_move(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('Aucune écriture comptable n\'est liée à ce marché.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Écriture comptable'),
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_stock_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mouvements de stock'),
            'res_model': 'lagunes.market.stock.move',
            'view_mode': 'list',
            'domain': [('market_id', '=', self.id)],
            'target': 'current',
        }
