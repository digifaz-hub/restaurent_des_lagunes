# -*- coding: utf-8 -*-
from odoo import models, fields


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        """Marque la proposition de menu comme 'envoyée' lorsque le composer
        a été ouvert depuis l'action `action_send_email` de la proposition."""
        result = super()._action_send_mail(auto_commit=auto_commit)
        if self.env.context.get('mark_proposition_as_sent'):
            Proposition = self.env['lagunes.traiteur.proposition']
            for wizard in self:
                if wizard.model != 'lagunes.traiteur.proposition':
                    continue
                res_ids = wizard._evaluate_res_ids() or []
                propositions = Proposition.browse(res_ids).exists()
                propositions.filtered(lambda p: p.state == 'draft').write({
                    'state': 'sent',
                    'date_envoi': fields.Datetime.now(),
                })
        return result
