# -*- coding: utf-8 -*-
from odoo import models, fields

class LagunesMarketAdjustmentWizard(models.TransientModel):
    _name = 'lagunes.market.adjustment.wizard'
    _description = 'Wizard Ajustement Manuel'

    stock_id = fields.Many2one('lagunes.market.stock', string='Stock', required=True)
    qty_delta = fields.Float(string='Quantité (+ ou -)', required=True, help="Utilisez une valeur positive pour un ajout, négative pour un retrait.")
    reason = fields.Char(string='Justification', required=True)

    def action_apply(self):
        self.ensure_one()
        self.stock_id.action_manual_adjustment(self.qty_delta, self.reason)
