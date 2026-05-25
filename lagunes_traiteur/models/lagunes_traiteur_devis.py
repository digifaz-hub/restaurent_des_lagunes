# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class LagunesTraiteurDevis(models.Model):
    _name = 'lagunes.traiteur.devis'
    _description = 'Devis Traiteur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    name = fields.Char(string='Référence Devis', readonly=True, copy=False, default=lambda self: _('Nouveau'))
    demande_id = fields.Many2one('lagunes.traiteur.demande', string='Demande source', required=True, ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='Devis Odoo', readonly=True)
    company_id = fields.Many2one('res.company', related='demande_id.company_id', store=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('accepted', 'Accepté'),
        ('refused', 'Refusé'),
        ('revised', 'Révisé')
    ], string='Statut', default='draft', tracking=True)
    
    date_envoi = fields.Datetime(string='Date d\'envoi')
    date_validite = fields.Date(string='Date d\'expiration')
    notes_devis = fields.Text(string='Conditions particulières')
    montant_total = fields.Monetary(string='Montant Total', related='sale_order_id.amount_total', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    
    # Champs pour gestion refus/modifications
    refusal_reason = fields.Text(string='Motif du refus', tracking=True)
    client_notes = fields.Text(string='Notes / Modifications du client', help='Notes ou modifications demandées par le client')
    revision_count = fields.Integer(string='Nombre de révisions', default=0, readonly=True)
    parent_devis_id = fields.Many2one('lagunes.traiteur.devis', string='Devis précédent', readonly=True)
    child_devis_ids = fields.One2many('lagunes.traiteur.devis', 'parent_devis_id', string='Révisions')

    def action_send_devis(self):
        """Envoie le devis par email avec le template dédié"""
        self.ensure_one()
        
        # Guard: state doit être draft
        if self.state != 'draft':
            raise UserError(_("Le devis doit être en 'Brouillon' pour être envoyé."))
        
        self.write({'state': 'sent', 'date_envoi': fields.Datetime.now()})
        
        # Synchronisation: le devis pilote la demande
        if self.demande_id:
            self.demande_id.write({'state': 'devis_envoye'})
        
        template = self.env.ref('lagunes_traiteur.email_template_envoi_devis', raise_if_not_found=False)
        if not template:
            return True  # Pas de template, mais action réussie
            
        # Ouverture de l'assistant de composition d'email pré-rempli
        return template.send_mail(self.id, force_send=False, raise_exception=False)

    def action_accept_devis(self):
        """Accepte le devis et met à jour la demande (sens unique Devis→Demande)"""
        self.ensure_one()
        
        # Guard: state doit être sent ou draft (cas réel: acceptation directe)
        if self.state not in ('sent', 'draft'):
            raise UserError(_("Le devis doit être envoyé pour être accepté."))
        
        self.write({'state': 'accepted'})
        
        # Synchronisation: le devis pilote la demande
        if self.demande_id:
            self.demande_id.action_accept()
        return True

    def action_refuse_devis(self):
        """Refuse le devis et met à jour la demande (sens unique Devis→Demande)"""
        self.ensure_one()
        
        # Guard: ne pas refuser un devis déjà finalisé
        if self.state in ('accepted', 'revised'):
            raise UserError(_("Impossible de refuser un devis déjà accepté ou révisé."))
        if not self.refusal_reason:
            raise UserError(_("Veuillez indiquer le motif du refus."))
        
        self.write({'state': 'refused'})
        
        # Synchronisation: le devis pilote la demande
        if self.demande_id:
            self.demande_id.action_refuse()
        return True

    def action_revise_devis(self):
        """Crée une nouvelle révision du devis (Modèle B: historique complet)"""
        self.ensure_one()
        
        # Guard: on peut réviser un devis envoyé, refusé ou accepté
        if self.state not in ('sent', 'refused', 'accepted'):
            raise UserError(_("Seuls les devis envoyés, refusés ou acceptés peuvent être révisés."))
        
        # Copier le devis avec sale_order (pour cohérence)
        new_devis = self.copy({
            'state': 'draft',
            'parent_devis_id': self.id,
            'revision_count': self.revision_count + 1,
            'name': _('Nouveau'),  # Sera régénéré par la séquence
            'sale_order_id': self.sale_order_id.id,  # Même sale.order
        })
        # Conserver les notes du client
        if self.client_notes:
            new_devis.client_notes = self.client_notes
        
        # Mettre l'ancien devis à l'état révisé
        self.write({'state': 'revised'})
        
        # Mise à jour de la demande: pointer vers le nouveau devis actif
        if self.demande_id:
            self.demande_id.write({'active_devis_id': new_devis.id})
        
        return {
            'name': _('Nouvelle Révision'),
            'type': 'ir.actions.act_window',
            'res_model': 'lagunes.traiteur.devis',
            'view_mode': 'form',
            'res_id': new_devis.id,
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('lagunes.traiteur.devis') or _('Nouveau')
        return super().create(vals_list)
