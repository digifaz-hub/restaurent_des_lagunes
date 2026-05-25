# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LagunesTraiteurConfig(models.Model):
    _name = 'lagunes.traiteur.config'
    _description = 'Configuration Traiteur'
    _rec_name = 'company_id'

    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    jours_avance_menu = fields.Integer(string='Marge affichage menu (jours)', default=3, help='Nombre de jours à l\'avance pour afficher le menu réel')
    email_reception_demandes = fields.Char(string='Email réception demandes')
    delai_reponse_devis_jours = fields.Integer(string='Délai de réponse (jours)', default=2)
    mentions_legales = fields.Html(string='CGV / Mentions légales')
    logo_portail = fields.Image(string='Logo du portail')
    titre_portail = fields.Char(string='Titre du portail', default='Service Traiteur — Restaurant des Lagunes')
    sous_titre_portail = fields.Char(string='Sous-titre', default='Qualité et excellence pour vos événements')
    couleur_primaire = fields.Char(string='Couleur primaire', default='#16166d')
    produit_prestation_id = fields.Many2one('product.product', string='Produit générique prestation', help='Produit utilisé sur les lignes de devis Odoo')

    portail_url = fields.Char(
        string='Lien du site traiteur',
        compute='_compute_portail_url',
        store=False,
        help='URL publique du portail de demande traiteur, à communiquer aux clients.',
    )

    @api.depends('company_id')
    def _compute_portail_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for config in self:
            config.portail_url = f"{base_url}/traiteur" if base_url else "/traiteur"

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', 'Une seule configuration par société !')
    ]

    @api.model
    def action_open_config(self):
        """Ouvre la config de la société courante (la crée si inexistante)"""
        config = self.search([('company_id', '=', self.env.company.id)], limit=1)
        if not config:
            config = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configuration Traiteur',
            'res_model': 'lagunes.traiteur.config',
            'view_mode': 'form',
            'res_id': config.id,
            'target': 'inline',
        }
