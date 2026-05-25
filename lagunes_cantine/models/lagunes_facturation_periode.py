# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class LagunesFacturationPeriode(models.Model):
    """
    Période de facturation mensuelle pour regrouper les commandes
    et générer des devis/factures consolidées.

    CORRECTIFS v2 :
    - _compute_invoice_id sans effets de bord
    - Contrainte anti-chevauchement
    - Workflow annulation unifié + reset draft
    - Anti double-facturation au chargement
    - Validation avant génération devis
    - Protection des commandes liées
    - Log + date de facturation
    - Duplication mois suivant
    """
    _name = 'lagunes.facturation.periode'
    _description = 'Période de facturation mensuelle'
    _order = 'date_start desc'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ------------------------------------------------------------------ #
    #  CHAMPS                                                              #
    # ------------------------------------------------------------------ #

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        index=True,
        tracking=True,
    )

    entreprise_id = fields.Many2one(
        'res.partner',
        string='Entreprise',
        required=True,
        domain=[('is_cantine_client', '=', True)],
        ondelete='cascade',
        index=True,
        tracking=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        ondelete='restrict',
        index=True,
        tracking=True,
    )

    date_start = fields.Date(
        string='Date de début',
        required=True,
        default=lambda self: date.today().replace(day=1),
        index=True,
        tracking=True,
    )

    date_end = fields.Date(
        string='Date de fin',
        required=True,
        index=True,
        tracking=True,
    )

    date_facturation = fields.Date(
        string='Date de facturation',
        readonly=True,
        copy=False,
        tracking=True,
        help='Date à laquelle la période a été marquée comme facturée.',
    )

    state = fields.Selection([
        ('draft',      'Brouillon'),
        ('confirmed',  'Confirmé'),
        ('invoiced',   'Facturé'),
        ('cancelled',  'Annulé'),
    ], string='État', default='draft', required=True, index=True, tracking=True)

    commande_ids = fields.Many2many(
        'lagunes.commande',
        'lagunes_facturation_commande_rel',
        'periode_id',
        'commande_id',
        string='Commandes',
        domain="[('entreprise_id', '=', entreprise_id), "
               "('date', '>=', date_start), "
               "('date', '<=', date_end), "
               "('state', 'in', ['delivered'])]",
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Devis/Commande',
        readonly=True,
        copy=False,
        ondelete='restrict',
    )

    # FIX #1 : compute pur, SANS effets de bord
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        readonly=True,
        copy=False,
        compute='_compute_invoice_id',
        store=True,
    )

    total_commandes = fields.Integer(
        string='Nombre de commandes',
        compute='_compute_totals',
        store=True,
    )

    total_jours = fields.Integer(
        string='Nombre de jours',
        compute='_compute_totals',
        store=True,
    )

    montant_total = fields.Float(
        string='Montant total',
        compute='_compute_totals',
        store=True,
    )

    notes = fields.Text(string='Notes')

    create_date = fields.Datetime(string='Date de création', readonly=True)
    create_uid = fields.Many2one('res.users', string='Créé par', readonly=True)

    # ------------------------------------------------------------------ #
    #  COMPUTE                                                             #
    # ------------------------------------------------------------------ #

    @api.depends('sale_order_id', 'sale_order_id.invoice_ids')
    def _compute_invoice_id(self):
        """
        FIX #1 — Compute pur : récupère uniquement la facture.
        Les transitions d'état se font EXCLUSIVEMENT dans action_mark_invoiced,
        appelé manuellement via le bouton ou un éventuel cron.
        """
        for periode in self:
            if periode.sale_order_id and periode.sale_order_id.invoice_ids:
                periode.invoice_id = periode.sale_order_id.invoice_ids[0]
            else:
                periode.invoice_id = False

    @api.depends('commande_ids', 'commande_ids.prix_total', 'commande_ids.date')
    def _compute_totals(self):
        for periode in self:
            periode.total_commandes = len(periode.commande_ids)
            dates = periode.commande_ids.mapped('date')
            periode.total_jours = len(set(dates))
            periode.montant_total = sum(periode.commande_ids.mapped('prix_total'))

    # ------------------------------------------------------------------ #
    #  CONTRAINTES                                                         #
    # ------------------------------------------------------------------ #

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for periode in self:
            if periode.date_end < periode.date_start:
                raise ValidationError(
                    _('La date de fin ne peut pas être antérieure à la date de début.')
                )

    @api.constrains('entreprise_id', 'company_id', 'date_start', 'date_end', 'state')
    def _check_no_overlap(self):
        """
        FIX #2 — Empêche les périodes chevauchantes pour la même entreprise et société.
        Les périodes annulées sont ignorées.
        """
        for periode in self:
            if periode.state == 'cancelled':
                continue
            overlap = self.search([
                ('id', '!=', periode.id),
                ('entreprise_id', '=', periode.entreprise_id.id),
                ('company_id', '=', periode.company_id.id),
                ('state', '!=', 'cancelled'),
                ('date_start', '<=', periode.date_end),
                ('date_end', '>=', periode.date_start),
            ], limit=1)
            if overlap:
                raise ValidationError(
                    _("La période chevauche avec '%(name)s' (%(start)s → %(end)s) "
                      "pour %(entreprise)s.\n"
                      "Modifiez les dates ou annulez d'abord la période existante.")
                    % {
                        'name': overlap.name,
                        'start': overlap.date_start.strftime('%d/%m/%Y'),
                        'end': overlap.date_end.strftime('%d/%m/%Y'),
                        'entreprise': periode.entreprise_id.name,
                    }
                )

    # ------------------------------------------------------------------ #
    #  CRUD                                                                #
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('lagunes.facturation.periode')
                    or _('Nouveau')
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------ #
    #  ACTIONS WORKFLOW                                                    #
    # ------------------------------------------------------------------ #

    def action_load_commandes(self):
        """
        FIX #4 — Charge les commandes livrées et non facturées.
        Exclut les commandes déjà dans une autre période active.
        Avertit si des commandes ont été exclues.
        """
        self.ensure_one()

        if self.state != 'draft':
            raise ValidationError(
                _('Impossible de recharger les commandes : '
                  'la période n\'est plus en brouillon.')
            )

        already_elsewhere = self._get_commandes_already_in_other_periode()

        commandes = self.env['lagunes.commande'].search([
            ('entreprise_id', '=', self.entreprise_id.id),
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_end),
            ('state', '=', 'delivered'),
            ('facturation_state', '=', 'not_invoiced'),
            ('id', 'not in', already_elsewhere.ids),
        ])

        self.commande_ids = [(6, 0, commandes.ids)]

        # Compter les commandes livrées totales pour signaler les exclusions
        total_delivered = self.env['lagunes.commande'].search_count([
            ('entreprise_id', '=', self.entreprise_id.id),
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_end),
            ('state', '=', 'delivered'),
        ])
        excluded = total_delivered - len(commandes)

        if excluded:
            msg = _(
                '%(loaded)d commande(s) chargée(s). '
                '%(excluded)d exclue(s) car déjà en cours de facturation.'
            ) % {'loaded': len(commandes), 'excluded': excluded}
            notif_type = 'warning'
            sticky = True
        else:
            msg = _('%d commande(s) chargée(s) pour la période.') % len(commandes)
            notif_type = 'success'
            sticky = False

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'title': _('Commandes chargées'),
                'message': msg,
                'type': notif_type,
                'sticky': sticky,
            }
        }

    def action_confirm(self):
        for periode in self:
            if not periode.commande_ids:
                raise ValidationError(
                    _('Impossible de confirmer une période sans commandes.\n'
                      'Utilisez le bouton "Charger les commandes" d\'abord.')
                )
            periode.state = 'confirmed'
            periode.message_post(body=_('Période confirmée.'))

    def action_generate_sale_order(self):
        """
        FIX #5 — Valide les commandes avant génération du devis :
        - prix à zéro
        - commandes déjà facturées
        """
        self.ensure_one()

        if self.sale_order_id:
            raise ValidationError(
                _('Un devis existe déjà pour cette période.\nRéférence : %s')
                % self.sale_order_id.name
            )

        if not self.commande_ids:
            raise ValidationError(_('Aucune commande sélectionnée pour générer le devis.'))

        # Vérifier les prix à zéro
        zero_price = self.commande_ids.filtered(lambda c: c.prix_total <= 0)
        if zero_price:
            plat_names = ', '.join([
                (c.resistance_plat_id.name or c.entree_plat_id.name or c.dessert_plat_id.name or 'Plat sans prix')
                for c in zero_price
            ])
            raise ValidationError(
                _('Les commandes suivantes ont un prix total à 0 : %(plats)s.\n'
                  'Veuillez corriger les prix avant de générer le devis.')
                % {'plats': plat_names}
            )

        # Vérifier que toutes les commandes sont encore "not_invoiced"
        already_invoiced = self.commande_ids.filtered(
            lambda c: c.facturation_state != 'not_invoiced'
        )
        if already_invoiced:
            raise ValidationError(
                _('%(count)d commande(s) ont déjà été facturées ou sont en cours '
                  'de facturation. Rechargez les commandes.')
                % {'count': len(already_invoiced)}
            )

        # Regrouper par plat principal (résistance) ou plat unique
        plat_summary = {}
        for commande in self.commande_ids:
            # Utiliser le plat de résistance comme clé principale, ou l'entrée, ou le dessert
            key_plat = commande.resistance_plat_id or commande.entree_plat_id or commande.dessert_plat_id
            if not key_plat:
                continue  # Ignorer les commandes sans plat
            key = key_plat.id
            if key not in plat_summary:
                plat_summary[key] = {
                    'plat': key_plat,
                    'quantity': 0,
                    'prix_total': 0,
                    'commandes': [],
                }
            plat_summary[key]['quantity'] += commande.quantity
            plat_summary[key]['prix_total'] += commande.prix_total
            plat_summary[key]['commandes'].append(commande)

        order_lines = [
            (0, 0, {
                'product_id': data['plat'].product_id.id,
                'name': self._build_line_description(data['commandes']),
                'product_uom_qty': data['quantity'],
                'price_unit': data['prix_total'] / data['quantity'] if data['quantity'] > 0 else 0,
            })
            for data in plat_summary.values()
        ]

        sale_order = self.env['sale.order'].create({
            'partner_id': self.entreprise_id.id,
            'company_id': self.company_id.id,
            'date_order': fields.Datetime.now(),
            'order_line': order_lines,
            'note': self._build_order_note(),
        })

        self.sale_order_id = sale_order.id
        self.commande_ids.write({'facturation_state': 'to_invoice'})
        self.message_post(
            body=_('Devis généré : <a href="#">%s</a>') % sale_order.name
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Devis généré'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_mark_invoiced(self):
        """
        FIX #1 — Seul endroit où l'état passe à 'invoiced'
        et où les commandes sont marquées 'invoiced'.
        Appelé manuellement via le bouton de la vue.
        """
        for periode in self:
            if not periode.invoice_id:
                raise ValidationError(_('Aucune facture trouvée pour cette période.'))
            if periode.invoice_id.state != 'posted':
                raise ValidationError(
                    _('La facture doit être validée (comptabilisée) '
                      'avant de marquer la période comme facturée.')
                )
            # ✅ Marquer les commandes EN PREMIER (si ce write échoue,
            # la période reste en état 'confirmed' → cohérence préservée)
            periode.commande_ids.write({'facturation_state': 'invoiced'})
            # Puis la période
            periode.write({
                'state': 'invoiced',
                'date_facturation': fields.Date.today(),
            })
            periode.message_post(
                body=_('Période facturée. Facture : %s') % periode.invoice_id.name
            )

    def action_cancel(self):
        """
        FIX #3 — Annulation unifiée avec gestion de la cascade devis.
        Remet les commandes à 'not_invoiced' si elles étaient en 'to_invoice'.
        """
        for periode in self:
            if periode.state == 'invoiced':
                raise ValidationError(
                    _('Impossible d\'annuler une période déjà facturée.')
                )

            if periode.sale_order_id:
                so = periode.sale_order_id
                if so.state == 'draft':
                    so.action_cancel()
                elif so.state == 'cancel':
                    pass  # déjà annulé
                else:
                    raise ValidationError(
                        _('Le bon de commande %(so)s est confirmé (état : %(state)s).\n'
                          'Annulez-le d\'abord depuis la commande de vente.')
                        % {'so': so.name, 'state': so.state}
                    )

            # Remettre les commandes à "non facturées"
            periode.commande_ids.filtered(
                lambda c: c.facturation_state == 'to_invoice'
            ).write({'facturation_state': 'not_invoiced'})

            periode.state = 'cancelled'
            periode.message_post(body=_('Période annulée.'))

    def action_reset_to_draft(self):
        """
        FIX #3 — Permet de repartir d'une période annulée.
        """
        for periode in self:
            if periode.state != 'cancelled':
                raise ValidationError(
                    _('Seules les périodes annulées peuvent être remises en brouillon.')
                )
            periode.state = 'draft'
            periode.message_post(body=_('Période remise en brouillon.'))

    def action_duplicate_next_month(self):
        """
        #9 — Duplique la période pour le mois suivant (sans commandes ni devis).
        """
        self.ensure_one()
        from dateutil.relativedelta import relativedelta

        new_start = self.date_start + relativedelta(months=1)
        new_end = self.date_end + relativedelta(months=1)

        new_periode = self.copy(default={
            'date_start': new_start,
            'date_end': new_end,
            'state': 'draft',
            'commande_ids': [(5, 0, 0)],
            'sale_order_id': False,
            'date_facturation': False,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lagunes.facturation.periode',
            'res_id': new_periode.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------ #
    #  ACTIONS VUES RAPIDES                                                #
    # ------------------------------------------------------------------ #

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise ValidationError(_('Aucun devis généré pour cette période.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Devis/Commande'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise ValidationError(_('Aucune facture générée pour cette période.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------ #
    #  HELPERS PRIVÉS                                                      #
    # ------------------------------------------------------------------ #

    def _get_commandes_already_in_other_periode(self):
        """Retourne les commandes déjà liées à une autre période non annulée."""
        other_periodes = self.search([
            ('id', '!=', self.id),
            ('entreprise_id', '=', self.entreprise_id.id),
            ('company_id', '=', self.company_id.id),
            ('state', 'not in', ['cancelled']),
        ])
        return other_periodes.mapped('commande_ids')

    def _build_line_description(self, commandes):
        # Construire une description avec tous les plats du menu
        descriptions = []
        for cmd in commandes[:5]:  # Limiter à 5 pour éviter les descriptions trop longues
            plats = []
            if cmd.entree_plat_id:
                plats.append(f"Entrée: {cmd.entree_plat_id.name}")
            if cmd.resistance_plat_id:
                plats.append(f"Plat: {cmd.resistance_plat_id.name}")
            if cmd.dessert_plat_id:
                plats.append(f"Dessert: {cmd.dessert_plat_id.name}")
            if plats:
                descriptions.append(' + '.join(plats))
        desc = ' | '.join(descriptions)
        if len(commandes) > 5:
            desc += f" | ... ({len(commandes) - 5} autres)"
        return desc

    def _build_order_note(self):
        """FIX #6 — Notes traduisibles via _()."""
        note = (
            _("Facturation mensuelle - Cantine d'entreprise") + "\n"
            + _("Période : du %(start)s au %(end)s") % {
                'start': self.date_start.strftime('%d/%m/%Y'),
                'end': self.date_end.strftime('%d/%m/%Y'),
            } + "\n"
            + _("Entreprise : %(name)s") % {'name': self.entreprise_id.name} + "\n"
            + _("Total commandes : %(total)d") % {'total': self.total_commandes} + "\n"
            + _("Nombre de jours : %(days)d") % {'days': self.total_jours}
        )
        if self.notes:
            note += "\n\n" + _("Notes :") + "\n" + self.notes
        return note