# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    traiteur_demande_id = fields.Many2one(
        'lagunes.traiteur.demande',
        string='Demande Traiteur',
        help='Demande traiteur à l\'origine de ce bon de commande'
    )

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    traiteur_prestation_id = fields.Many2one(
        'lagunes.traiteur.demande.prestation',
        string='Prestation Traiteur',
        help='Prestation traiteur à l\'origine de cette ligne'
    )
    traiteur_nb_jours = fields.Integer(string='Nombre de jours (Traiteur)', default=1)

