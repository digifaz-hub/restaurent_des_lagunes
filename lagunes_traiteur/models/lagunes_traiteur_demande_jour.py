# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class LagunesTraiteurDemandeJour(models.Model):
    _name = 'lagunes.traiteur.demande.jour'
    _description = 'Jour de Prestation Traiteur'
    _order = 'date, id'
    _check_company_auto = True

    demande_id = fields.Many2one('lagunes.traiteur.demande', string='Demande', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    jour_semaine = fields.Char(string='Jour', compute='_compute_jour_semaine')
    
    week_menu_id = fields.Many2one('lagunes.week.menu', string='Menu hebdomadaire source')
    prestation_ids = fields.One2many('lagunes.traiteur.demande.prestation', 'jour_id', string='Prestations du jour')
    notes = fields.Text(string='Notes / Allergies')
    is_menu_disponible = fields.Boolean(string='Menu publié', default=False)


    @api.depends('date')
    def _compute_jour_semaine(self):
        jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        for rec in self:
            if rec.date:
                rec.jour_semaine = jours[rec.date.weekday()]
            else:
                rec.jour_semaine = ""
    def action_open_day_menu(self):
        self.ensure_one()
        return {
            'name': _('Détails du %s (%s)') % (self.jour_semaine, self.date),
            'type': 'ir.actions.act_window',
            'res_model': 'lagunes.traiteur.demande.jour',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
