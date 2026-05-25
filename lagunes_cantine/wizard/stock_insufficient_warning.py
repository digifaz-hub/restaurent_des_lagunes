# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json


class StockInsufficientWarning(models.TransientModel):
    """Wizard d'avertissement pour stock insuffisant lors de la préparation commande"""

    _name = 'lagunes.stock.insufficient.warning'
    _description = 'Avertissement stock insuffisant'

    # ═══════════════════════════════════════════════════════════════════════
    # CHAMPS PRINCIPAUX
    # ═══════════════════════════════════════════════════════════════════════

    commande_ids = fields.Many2many(
        comodel_name='lagunes.commande',
        string='Commandes concernées',
        readonly=True,
    )

    new_state = fields.Char(
        string='Nouvel état cible',
        readonly=True,
    )

    can_proceed = fields.Boolean(
        string='Peut continuer',
        compute='_compute_can_proceed',
    )

    has_critical = fields.Boolean(
        string='Rupture totale',
        compute='_compute_can_proceed',
    )

    # ═══════════════════════════════════════════════════════════════════════
    # LIGNES DE DÉTAIL
    # ═══════════════════════════════════════════════════════════════════════

    warning_line_ids = fields.One2many(
        comodel_name='lagunes.stock.warning.line',
        inverse_name='warning_id',
        string='Détails des manquants',
        readonly=True,
    )

    summary_text = fields.Text(
        string='Résumé',
        compute='_compute_summary_text',
    )

    # ═══════════════════════════════════════════════════════════════════════
    # OPTIONS
    # ═══════════════════════════════════════════════════════════════════════

    force_reason = fields.Text(
        string='Justification du forçage',
        help='Obligatoire si vous forcez malgré stock insuffisant. Min 10 caractères.',
    )

    notify_manager = fields.Boolean(
        string='Notifier le responsable',
        default=True,
        help='Envoyer une notification au responsable stock',
    )

    # ═══════════════════════════════════════════════════════════════════════
    # COMPUTE METHODS
    # ═══════════════════════════════════════════════════════════════════════

    @api.depends('warning_line_ids')
    def _compute_can_proceed(self):
        """Détermine si on peut continuer (au moins un article avec stock > 0)"""
        for warning in self:
            # Peut continuer si au moins une ligne a du stock disponible
            warning.can_proceed = any(
                line.available_qty > 0 for line in warning.warning_line_ids
            )
            # Critique si au moins une ligne a 0 de disponible
            warning.has_critical = any(
                line.available_qty == 0 for line in warning.warning_line_ids
            )

    @api.depends('warning_line_ids')
    def _compute_summary_text(self):
        """Génère un résumé textuel des manquants"""
        for warning in self:
            if not warning.warning_line_ids:
                warning.summary_text = _('Aucun problème de stock.')
                continue

            lines = []
            for line in warning.warning_line_ids:
                status = '🔴' if line.available_qty == 0 else '🟠'
                lines.append(
                    f"{status} {line.article_name}: "
                    f"demandé {line.requested_qty:.2f} {line.unit}, "
                    f"dispo {line.available_qty:.2f} {line.unit}, "
                    f"manque {line.missing_qty:.2f} {line.unit}"
                )

            warning.summary_text = '\n'.join(lines)

    # ═══════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def action_cancel(self):
        """Annuler l'opération - retour sans changement"""
        return {'type': 'ir.actions.act_window_close'}

    def action_force_continue(self):
        """Forcer la continuation malgré stock insuffisant"""
        self.ensure_one()

        # Validation justification
        if not self.force_reason or len(self.force_reason.strip()) < 10:
            raise ValidationError(_(
                "Une justification d'au moins 10 caractères est obligatoire "
                "pour forcer une déduction avec stock insuffisant."
            ))

        # Préparer les détails pour historique
        missing_details = []
        for line in self.warning_line_ids:
            missing_details.append({
                'article_id': line.article_id.id,
                'article_name': line.article_id.name,
                'requested': line.requested_qty,
                'available': line.available_qty,
                'missing': line.missing_qty,
                'unit': line.unit,
            })

        now = fields.Datetime.now()

        # Traiter chaque commande
        for commande in self.commande_ids:
            # Marquer comme forcée avec tous les détails
            commande.write({
                'stock_forced_by_id': self.env.user.id,
                'stock_forced_date': now,
                'stock_insufficient_details': json.dumps(missing_details, ensure_ascii=False),
            })

            # Logger dans le chatter
            commande.message_post(
                body=_("<strong>⚠️ Stock insuffisant accepté</strong><br/>"
                       "Forçage par : %s<br/>"
                       "Date : %s<br/>"
                       "Justification : %s<br/><br/>"
                       "<strong>Détails des manquants :</strong><br/>%s") % (
                    self.env.user.name,
                    now.strftime('%d/%m/%Y %H:%M'),
                    self.force_reason,
                    self.summary_text.replace('\n', '<br/>'),
                ),
                subtype_xmlid='mail.mt_note',
            )

            # Poursuivre avec déduction autorisée
            commande._deduct_ingredients_from_market(
                allow_insufficient=True,
                forced=True,
            )

            # Changer le statut
            commande.state = self.new_state

        # Notification si demandée
        if self.notify_manager:
            self._notify_stock_managers(missing_details)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Stock insuffisant accepté'),
                'message': _('%s commande(s) traitées avec forçage.') % len(self.commande_ids),
                'type': 'warning',
                'sticky': True,
            }
        }

    def _notify_stock_managers(self, missing_details):
        """Notifier les responsables stock des manquants"""
        # Trouver utilisateurs avec droits stock
        stock_managers = self.env.ref('lagunes_market.group_lagunes_market_manager').users

        if not stock_managers:
            return

        # Préparer message
        articles_list = '\n'.join([
            f"- {d['article_name']}: manque {d['missing']:.2f} {d['unit']}"
            for d in missing_details
        ])

        message = _(
            "⚠️ **Stock insuffisant accepté**\n\n"
            "Des commandes ont été validées malgré un stock insuffisant :\n\n"
            "%s\n\n"
            "Forçage par : %s\n"
            "Date : %s"
        ) % (
            articles_list,
            self.env.user.name,
            fields.Datetime.now().strftime('%d/%m/%Y %H:%M'),
        )

        # Envoyer notification Odoo
        for manager in stock_managers:
            self.env['bus.bus']._sendone(
                manager.partner_id,
                'lagunes.stock.insufficient_alert',
                {'message': message}
            )


class StockWarningLine(models.TransientModel):
    """Ligne de détail pour un article manquant"""

    _name = 'lagunes.stock.warning.line'
    _description = 'Ligne de détail stock insuffisant'

    warning_id = fields.Many2one(
        comodel_name='lagunes.stock.insufficient.warning',
        required=True,
        ondelete='cascade',
    )

    article_id = fields.Many2one(
        comodel_name='lagunes.market.article',
        string='Article',
        readonly=True,
    )

    article_name = fields.Char(
        string='Nom article',
        related='article_id.name',
        readonly=True,
    )

    requested_qty = fields.Float(
        string='Quantité demandée',
        readonly=True,
    )

    available_qty = fields.Float(
        string='Quantité disponible',
        readonly=True,
    )

    missing_qty = fields.Float(
        string='Quantité manquante',
        readonly=True,
    )

    unit = fields.Char(
        string='Unité',
        readonly=True,
    )

    is_critical = fields.Boolean(
        string='Rupture',
        compute='_compute_is_critical',
    )

    @api.depends('available_qty')
    def _compute_is_critical(self):
        for line in self:
            line.is_critical = line.available_qty == 0
