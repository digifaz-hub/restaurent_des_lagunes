# -*- coding: utf-8 -*-
"""
Patch d'``ir.actions.report`` pour forcer ``--encoding utf-8`` lors de
l'invocation de wkhtmltopdf.

Contexte
========
Odoo 18 ne passe pas explicitement ``--encoding`` à wkhtmltopdf et se
repose sur la balise ``<meta charset="utf-8">`` du template
``web.minimal_layout``. Or wkhtmltopdf 0.12.6 (patched Qt) sur Windows
ignore parfois cette balise et tombe sur l'encodage système (cp1252),
ce qui produit des mojibakes (``Ã©`` au lieu de ``é``,
``â€"`` au lieu de ``—``, etc.).

Ce patch ajoute systématiquement le flag ``--encoding utf-8`` à la
liste d'arguments construite par ``_build_wkhtmltopdf_args``.
"""
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _build_wkhtmltopdf_args(self, *args, **kwargs):
        command_args = super()._build_wkhtmltopdf_args(*args, **kwargs)
        # Garde-fou : ne pas dupliquer si Odoo (ou un autre module) l'a déjà ajouté.
        if '--encoding' not in command_args:
            command_args = list(command_args) + ['--encoding', 'utf-8']
        return command_args
