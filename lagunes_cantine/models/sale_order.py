# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_to_text = fields.Char(
        string='Montant en lettres',
        compute='_compute_amount_to_text',
        help='Montant total en lettres (utilisé dans le rapport devis Lagunes)'
    )

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_to_text(self):
        for order in self:
            if order.currency_id:
                order.amount_to_text = order.currency_id.amount_to_text(order.amount_total)
            else:
                order.amount_to_text = ""
