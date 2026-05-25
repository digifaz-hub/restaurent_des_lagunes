# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'

    nb_jours = fields.Integer(
        string='Nombre de jours',
        default=1,
        help='Nombre de jours de prestation (utilisé dans le rapport devis Lagunes)'
    )