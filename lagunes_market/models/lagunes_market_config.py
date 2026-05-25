# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Extension des paramètres de configuration Odoo pour le module lagunes_market.
    Expose deux paramètres comptables configurables :
    - Compte de dépense marché (account.account de type expense)
    - Journal de dépense marché (account.journal de type cash/bank/general)
    Ces valeurs sont stockées dans ir.config_parameter.
    """
    _inherit = 'res.config.settings'

    lagunes_market_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Compte de dépense marché',
        domain="[('account_type', 'like', 'expense')]",
        help='Compte comptable débité lors de la validation d\'un marché (type Dépense)',
        config_parameter='lagunes_market.account_id',
    )
    lagunes_market_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal de dépense marché',
        domain="[('type', 'in', ['cash', 'bank', 'general'])]",
        help='Journal utilisé pour les écritures comptables des marchés (caisse, banque ou général)',
        config_parameter='lagunes_market.journal_id',
    )
