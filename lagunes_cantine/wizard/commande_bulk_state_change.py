# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CommandeBulkStateChangeWizard(models.TransientModel):
    """Wizard pour modifier en masse le statut de plusieurs commandes"""
    
    _name = 'lagunes.commande.bulk.state.change'
    _description = 'Modification groupée des statuts de commandes'
    
    commande_ids = fields.Many2many(
        'lagunes.commande',
        string='Commandes sélectionnées',
        readonly=True
    )

    entreprise_id = fields.Many2one(
        'res.partner',
        string='Entreprise',
        domain="[('is_cantine_client', '=', True)]",
        help="Entreprise concernée. Pré-remplie si toutes les commandes sélectionnées appartiennent à la même."
    )

    new_state = fields.Selection([
        ('draft',      'Brouillon'),
        ('confirmed',  'Confirmée'),
        ('preparing',  'En préparation'),
        ('ready',      'Prêt'),
        ('delivered',  'Livré'),
        ('cancelled',  'Annulé'),
    ], string='Nouveau statut', required=True)

    apply_to_all_partner = fields.Boolean(
        string='Appliquer à toutes les commandes de cette entreprise',
        default=False,
        help='Si coché, la modification s\'appliquera à TOUTES les commandes non livrées de l\'entreprise sélectionnée ci-dessus.'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids') or []
        if active_ids:
            commandes = self.env['lagunes.commande'].browse(active_ids)
            res['commande_ids'] = [(6, 0, commandes.ids)]
            partners = commandes.mapped('entreprise_id')
            if len(partners) == 1:
                res['entreprise_id'] = partners.id
        return res
    
    notes = fields.Text(
        string='Notes (optionnel)',
        help='Notes additionnelles à ajouter à toutes les commandes'
    )
    
    def action_apply_state_change(self):
        """Appliquer le changement de statut avec vérification stock"""
        # Déterminer les commandes à traiter
        if self.apply_to_all_partner:
            partner = self.entreprise_id or (self.commande_ids[:1].entreprise_id)
            if not partner:
                raise ValidationError(_("Sélectionnez l'entreprise pour appliquer le changement à toutes ses commandes."))
            commandes = self.env['lagunes.commande'].search([
                ('entreprise_id', '=', partner.id),
                ('state', '!=', 'delivered'),
                ('state', '!=', 'cancelled'),
            ])
        elif self.entreprise_id:
            commandes = self.commande_ids.filtered(lambda c: c.entreprise_id == self.entreprise_id)
        else:
            commandes = self.commande_ids

        if not commandes:
            raise ValidationError(_('Aucune commande sélectionnée'))

        # ═════════════════════════════════════════════════════════════════════
        # VÉRIFICATION STOCK POUR PASSAGE EN PRÉPARATION
        # ═════════════════════════════════════════════════════════════════════
        if self.new_state == 'preparing':
            # Filtrer commandes dont stock pas encore déduit
            commandes_to_check = commandes.filtered(lambda c: not c.is_stock_deducted)

            if commandes_to_check:
                # Calculer besoins totaux cumulés
                stock_check = self._check_bulk_stock_availability(commandes_to_check)

                if not stock_check['sufficient']:
                    # Stock insuffisant, ouvrir wizard
                    return self._open_bulk_stock_warning(commandes_to_check, stock_check)

        # ═════════════════════════════════════════════════════════════════════
        # APPLICATION NORMALE
        # ═════════════════════════════════════════════════════════════════════
        for commande in commandes:
            commande.action_bulk_state_change(self.new_state)

            if self.notes:
                if commande.notes:
                    commande.notes += f'\n\n[{fields.Datetime.now()}] {self.notes}'
                else:
                    commande.notes = self.notes

        # Message de confirmation
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Succès'),
                'message': _(f'{len(commandes)} commande(s) mises à jour'),
                'sticky': False,
            }
        }

    def _check_bulk_stock_availability(self, commandes):
        """Vérifie le stock pour plusieurs commandes cumulées.

        Returns:
            dict avec 'sufficient', 'missing_lines', 'can_proceed'
        """
        # Agréger besoins par article
        article_needs = {}

        for commande in commandes:
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

                    article_id = ingredient.market_article_id.id
                    quantity_raw = ingredient.quantity * commande.quantity
                    quantity_needed = ingredient.unit_id.compute_quantity(
                        quantity_raw,
                        ingredient.market_article_id.default_uom_id
                    )

                    if article_id not in article_needs:
                        article_needs[article_id] = {
                            'article': ingredient.market_article_id,
                            'requested': 0.0,
                        }
                    article_needs[article_id]['requested'] += quantity_needed

        # Vérifier disponibilité
        missing_lines = []
        can_proceed = True

        for article_id, needs in article_needs.items():
            stock = self.env['lagunes.market.stock'].search([
                ('article_id', '=', article_id),
                ('company_id', '=', self.env.company.id),
            ], limit=1)

            available = stock.qty if stock else 0.0
            requested = needs['requested']
            missing = max(0.0, requested - available)

            if missing > 0:
                missing_lines.append({
                    'article_id': article_id,
                    'article_name': needs['article'].name,
                    'requested': requested,
                    'available': available,
                    'missing': missing,
                    'unit': needs['article'].default_uom or '',
                })
                if available == 0:
                    can_proceed = False

        return {
            'sufficient': len(missing_lines) == 0,
            'missing_lines': missing_lines,
            'can_proceed': can_proceed,
        }

    def _open_bulk_stock_warning(self, commandes, stock_check):
        """Ouvre le wizard d'avertissement pour changement en masse"""
        # Créer le wizard
        wizard = self.env['lagunes.stock.insufficient.warning'].create({
            'new_state': self.new_state,
        })

        # Lier toutes les commandes
        wizard.commande_ids = [(6, 0, commandes.ids)]

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
            'name': _('⚠️ Stock insuffisant (modification groupée)'),
            'res_model': 'lagunes.stock.insufficient.warning',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_ids': commandes.ids},
        }
