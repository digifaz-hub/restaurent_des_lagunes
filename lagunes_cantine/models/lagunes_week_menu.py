# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
import io
import base64

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class LagunesWeekMenu(models.Model):
    """Menu hebdomadaire de la cantine (Samedi à Vendredi)"""

    _name = 'lagunes.week.menu'
    _description = 'Menu hebdomadaire de cantine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'week_start_date desc'

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    name = fields.Char(
        string='Semaine',
        compute='_compute_name',
        store=True
    )

    week_start_date = fields.Date(
        string='Date de début (Samedi)',
        required=True,
        index=True,
        tracking=True
    )

    week_end_date = fields.Date(
        string='Date de fin (Vendredi)',
        compute='_compute_week_end_date',
        store=True
    )

    # Menu global ou par entreprise
    is_global = fields.Boolean(
        string='Menu global',
        default=True,
        help='Si coché, ce menu s\'applique à toutes les entreprises clientes',
        tracking=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Entreprise (si non global)',
        domain=[('is_cantine_client', '=', True)],
        ondelete='cascade',
        tracking=True
    )

    # Menu par jour et par type de plat
    menu_line_ids = fields.One2many(
        'lagunes.week.menu.line',
        'week_menu_id',
        string='Plats de la semaine'
    )

    # ── NOUVEAU : plats disponibles hors menu ─────────────────────────────
    hors_menu_plat_ids = fields.Many2many(
        'lagunes.plat',
        'lagunes_week_menu_hors_menu_rel',
        'week_menu_id',
        'plat_id',
        string='Plats disponibles hors menu',
        domain=[('active', '=', True)],
        help=(
            'Plats proposés sur le portail en dehors du menu de la semaine '
            '(section "Menu personnalisé"). '
            'Cochez également "Disponible hors menu" sur la fiche du plat.'
        )
    )

    notes = fields.Text(
        string='Notes générales',
        translate=True
    )

    active = fields.Boolean(
        string='Actif',
        default=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('published', 'Publié'),
        ('closed', 'Clôturé'),
    ], string='Statut', default='draft', tracking=True)

    # Stats
    menu_line_count = fields.Integer(
        string='Nombre de lignes',
        compute='_compute_menu_line_count',
        store=True
    )

    plat_count = fields.Integer(
        string='Nombre de plats',
        compute='_compute_plat_count',
        store=True
    )

    # Indique si la semaine est déjà terminée (week_end_date < aujourd'hui).
    # Non stocké : dépend de la date courante, doit être recalculé à la volée.
    is_past = fields.Boolean(
        string='Semaine passée',
        compute='_compute_is_past',
        search='_search_is_past',
        help="Vrai si la semaine est terminée (date de fin dépassée)."
    )

    @api.depends('menu_line_ids')
    def _compute_menu_line_count(self):
        for menu in self:
            menu.menu_line_count = len(menu.menu_line_ids)

    @api.depends('menu_line_ids.plat_ids')
    def _compute_plat_count(self):
        for menu in self:
            menu.plat_count = len(set(menu.menu_line_ids.mapped('plat_ids').ids))

    @api.depends('week_end_date')
    def _compute_is_past(self):
        today = fields.Date.context_today(self)
        for menu in self:
            menu.is_past = bool(menu.week_end_date and menu.week_end_date < today)

    def _search_is_past(self, operator, value):
        """Rendre le champ calculé 'is_past' utilisable dans les filtres."""
        today = fields.Date.context_today(self)
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValueError(_("Opérateur non supporté pour is_past : %s") % operator)
        want_past = value if operator == '=' else not value
        if want_past:
            return [('week_end_date', '<', today)]
        return ['|', ('week_end_date', '=', False), ('week_end_date', '>=', today)]

    @api.depends('week_start_date')
    def _compute_name(self):
        for record in self:
            if record.week_start_date:
                end = record.week_start_date + timedelta(days=6)
                record.name = f"Semaine du {record.week_start_date.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}"
            else:
                record.name = 'Semaine non définie'

    @api.depends('week_start_date')
    def _compute_week_end_date(self):
        for record in self:
            if record.week_start_date:
                record.week_end_date = record.week_start_date + timedelta(days=6)
            else:
                record.week_end_date = False

    # NOTE: l'ancien onchange `_onchange_week_start_date` pré-remplissait
    # automatiquement 7 lignes (une par jour) avec uniquement le champ `day`.
    # Or `plat_type_id` et `plat_ids` sont requis sur `lagunes.week.menu.line`,
    # ce qui empêchait la sauvegarde du menu (erreur de validation).
    # L'auto-création est désormais supprimée : l'utilisateur ajoute ses
    # lignes manuellement via le bouton « Ajouter une ligne » du tableau.

    def action_publish(self):
        """Publier le menu hebdomadaire"""
        for menu in self:
            menu.state = 'published'

    def action_close(self):
        """Fermer le menu hebdomadaire"""
        for menu in self:
            menu.state = 'closed'

    def action_reset_to_draft(self):
        """Remettre un menu publié ou clôturé en brouillon pour correction.

        Réservé aux managers cantine. Permet de modifier les dates, la portée
        et les lignes de menu sans devoir cloner l'enregistrement.
        """
        if not self.env.user.has_group('lagunes_cantine.group_lagunes_manager'):
            raise UserError(_(
                "Seul un manager Cantine peut remettre un menu hebdomadaire "
                "en brouillon."
            ))
        for menu in self:
            if menu.state == 'draft':
                continue
            menu.state = 'draft'
            menu.message_post(body=_(
                "Menu remis en brouillon par %s pour modification."
            ) % self.env.user.name)

    # ──────────────────────────────────────────────────────────────────
    #  CONTRAINTES MÉTIER
    # ──────────────────────────────────────────────────────────────────

    @api.constrains('week_start_date')
    def _check_week_start_is_saturday(self):
        """La semaine de cantine couvre Samedi → Vendredi.

        On impose donc que week_start_date tombe un samedi (weekday() == 5
        en Python : Mon=0, Tue=1, …, Sat=5, Sun=6). Sans cette contrainte,
        le controller portail (qui cherche `week_start_date = samedi courant`)
        ne retrouverait jamais un menu saisi un autre jour.
        """
        jours = [
            _('lundi'), _('mardi'), _('mercredi'), _('jeudi'),
            _('vendredi'), _('samedi'), _('dimanche'),
        ]
        for menu in self:
            if menu.week_start_date and menu.week_start_date.weekday() != 5:
                raise ValidationError(_(
                    "La date de début du menu hebdomadaire doit être un "
                    "samedi. La date choisie (%(date)s) est un %(jour)s."
                ) % {
                    'date': menu.week_start_date.strftime('%d/%m/%Y'),
                    'jour': jours[menu.week_start_date.weekday()],
                })

    @api.constrains('week_start_date', 'is_global', 'partner_id', 'state',
                    'active', 'company_id')
    def _check_no_overlap(self):
        """Interdit deux menus publiés & actifs pour la même semaine dans
        la même portée (global, ou même partner_id) et la même société.

        Les menus en brouillon ou clôturés peuvent coexister, seuls les
        menus qui seraient *réellement* affichés en même temps sont vérifiés.
        """
        for menu in self:
            if menu.state != 'published' or not menu.active or not menu.week_start_date:
                continue
            domain = [
                ('id', '!=', menu.id),
                ('company_id', '=', menu.company_id.id),
                ('week_start_date', '=', menu.week_start_date),
                ('state', '=', 'published'),
                ('active', '=', True),
            ]
            if menu.is_global:
                domain.append(('is_global', '=', True))
            else:
                domain += [('is_global', '=', False),
                           ('partner_id', '=', menu.partner_id.id)]
            conflict = self.search(domain, limit=1)
            if conflict:
                scope = _("global") if menu.is_global else _(
                    "pour l'entreprise « %s »") % (menu.partner_id.name or '')
                raise ValidationError(_(
                    "Un autre menu publié existe déjà pour la semaine du %(date)s "
                    "(%(scope)s) : « %(other)s ». "
                    "Clôturez-le ou désactivez-le avant de publier celui-ci."
                ) % {
                    'date': menu.week_start_date.strftime('%d/%m/%Y'),
                    'scope': scope,
                    'other': conflict.name or conflict.display_name,
                })

    # ──────────────────────────────────────────────────────────────────
    #  CRON : clôture automatique des menus dépassés
    # ──────────────────────────────────────────────────────────────────

    @api.model
    def _cron_auto_close_past_menus(self):
        """Bascule en 'closed' tout menu publié dont la semaine est terminée.

        Exécuté quotidiennement. Ne touche pas aux menus en brouillon
        (qui peuvent être des brouillons volontairement datés dans le passé).
        """
        today = fields.Date.context_today(self)
        past_menus = self.search([
            ('state', '=', 'published'),
            ('week_end_date', '<', today),
        ])
        if past_menus:
            past_menus.write({'state': 'closed'})
            _logger.info(
                "Auto-clôture de %s menu(s) hebdomadaire(s) expiré(s) : %s",
                len(past_menus), past_menus.mapped('name'),
            )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Copie automatiquement les notes de la semaine précédente"""
        menus = super().create(vals_list)

        for menu in menus:
            prev_week_date = menu.week_start_date - timedelta(days=7)
            prev_menu_domain = [
                ('week_start_date', '=', prev_week_date),
                ('active', '=', True),
            ]

            if menu.is_global:
                prev_menu_domain.append(('is_global', '=', True))
            else:
                prev_menu_domain.append(('partner_id', '=', menu.partner_id.id))

            prev_menu = self.search(prev_menu_domain, limit=1)

            if prev_menu:
                if prev_menu.notes and not menu.notes:
                    menu.notes = prev_menu.notes

                for line in menu.menu_line_ids:
                    prev_line = prev_menu.menu_line_ids.filtered(
                        lambda l: l.day == line.day and l.plat_type_id == line.plat_type_id
                    )
                    if prev_line and not line.notes:
                        line.notes = prev_line.notes
                    if prev_line and not line.notes_day:
                        line.notes_day = prev_line.notes_day

        return menus

    def action_export_excel(self):
        """Exporter le menu de la semaine en Excel"""
        if not xlsxwriter:
            raise UserError(_("La bibliothèque 'xlsxwriter' est requise pour l'export Excel."))

        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Menu de la semaine")
        sheet.set_landscape()

        # Styles — sans couleurs (tableau noir &amp; blanc).
        title_style = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
        header_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        day_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        cat_style = workbook.add_format({'bold': True, 'border': 1, 'valign': 'vcenter'})
        cell_style = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top', 'align': 'center'})
        notes_title_style = workbook.add_format({'bold': True, 'top': 2})
        notes_style = workbook.add_format({'text_wrap': True, 'valign': 'top'})
        client_style = workbook.add_format({'align': 'center', 'italic': True})

        # En-tête — coordonnées numériques (first_row, first_col, last_row, last_col, data, format).
        sheet.merge_range(0, 0, 0, 7, self.name, title_style)
        if not self.is_global and self.partner_id:
            sheet.merge_range(1, 0, 1, 7, f"Client : {self.partner_id.name}", client_style)
        
        # Colonnes
        sheet.set_column('A:A', 20)
        sheet.set_column('B:H', 25)

        # Header Jours
        days = [('0', 'SAMEDI'), ('1', 'DIMANCHE'), ('2', 'LUNDI'), ('3', 'MARDI'), ('4', 'MERCREDI'), ('5', 'JEUDI'), ('6', 'VENDREDI')]
        sheet.write(3, 0, "CATÉGORIES", header_style)
        for i, (day_code, day_name) in enumerate(days):
            col = i + 1
            date_str = ""
            if self.week_start_date:
                d = self.week_start_date + timedelta(days=i)
                date_str = f"\n({d.strftime('%d/%m')})"
            sheet.write(3, col, day_name + date_str, day_style)

        row = 4
        lines = self.menu_line_ids

        # Helper : pour les plats de résistance, display_name_website renvoie
        # "plat / accompagnement". Pour les autres, il renvoie le nom simple.
        def _plats_text(day_lines):
            names = []
            for line in day_lines:
                for plat in line.plat_ids:
                    names.append(plat.display_name_website or plat.name or '')
            return "\n".join(names)

        # 1. Entrées
        sheet.write(row, 0, "ENTRÉES", cat_style)
        for d in range(7):
            day_lines = lines.filtered(lambda l: int(l.day) == d and 'entr' in l.plat_type_id.name.lower())
            sheet.write(row, d + 1, _plats_text(day_lines), cell_style)
        row += 1

        # 2. Résistances (regroupés par catégorie de menu)
        all_cats = lines.mapped('menu_category_id').sorted('name')
        for cat in all_cats:
            sheet.write(row, 0, cat.name, cat_style)
            for d in range(7):
                day_lines = lines.filtered(lambda l: int(l.day) == d and l.menu_category_id == cat)
                sheet.write(row, d + 1, _plats_text(day_lines), cell_style)
            row += 1

        # 3. Desserts
        sheet.write(row, 0, "DESSERTS", cat_style)
        for d in range(7):
            day_lines = lines.filtered(lambda l: int(l.day) == d and 'dessert' in l.plat_type_id.name.lower())
            sheet.write(row, d + 1, _plats_text(day_lines), cell_style)
        row += 2

        # Notes
        if self.notes:
            sheet.merge_range(row, 0, row, 7, "Notes Générales :", notes_title_style)
            row += 1
            sheet.merge_range(row, 0, row + 2, 7, self.notes, notes_style)

        workbook.close()
        output.seek(0)
        
        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name}.xlsx",
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class LaguesWeekMenuLine(models.Model):
    """Ligne de menu hebdomadaire : jour + type de plat + plat"""

    _name = 'lagunes.week.menu.line'
    _description = 'Ligne de menu hebdomadaire'
    _order = 'week_menu_id, day, plat_type_id, sequence'
    _sql_constraints = [
        ('unique_menu_day_type', 'unique(week_menu_id, day, plat_type_id)',
         'Un seul type de plat par jour et par menu hebdomadaire.'),
    ]

    week_menu_id = fields.Many2one(
        'lagunes.week.menu',
        string='Menu de la semaine',
        required=True,
        ondelete='cascade'
    )

    day = fields.Selection([
        ('0', 'Samedi'),
        ('1', 'Dimanche'),
        ('2', 'Lundi'),
        ('3', 'Mardi'),
        ('4', 'Mercredi'),
        ('5', 'Jeudi'),
        ('6', 'Vendredi'),
    ], string='Jour', required=True, index=True)

    plat_type_id = fields.Many2one(
        'lagunes.plat.type',
        string='Type de plat',
        required=True,
        ondelete='restrict'
    )

    # Indique si ce type de plat est un plat de résistance (calculé)
    is_resistance = fields.Boolean(
        string='Est un plat de résistance',
        compute='_compute_is_resistance',
        store=True,
        help='Déterminé automatiquement depuis le type de plat.'
    )

    # Catégorie de menu — uniquement pour les plats de résistance
    menu_category_id = fields.Many2one(
        'lagunes.menu.category',
        string='Catégorie de menu',
        required=False,
        ondelete='set null',
        help=(
            'Applicable uniquement aux plats de résistance (Menu Africain, Européen, etc.).\n'
            'Ce champ est désactivé pour les lignes Entrée et Dessert.'
        )
    )

    plat_ids = fields.Many2many(
        'lagunes.plat',
        'lagunes_week_menu_line_plat_rel',
        'menu_line_id',
        'plat_id',
        string='Plats disponibles'
    )

    notes = fields.Text(
        string='Notes',
        translate=True
    )

    notes_day = fields.Text(
        string='Notes du jour',
        translate=True,
        help='Notes affichées sur le site pour ce jour du menu'
    )

    sequence = fields.Integer(
        string='Séquence',
        default=10
    )

    # ── COMPUTE ──────────────────────────────────────────────────────────

    @staticmethod
    def _is_plat_resistance(type_name):
        """Logique centralisée : détermine si un nom de type correspond à un plat de résistance.
        Strict : uniquement les types contenant 'résistance' ou 'principal'.
        """
        name = (type_name or '').lower()
        if not name:
            return False
        return ('sist' in name or 'principal' in name)

    @api.depends('plat_type_id', 'plat_type_id.name')
    def _compute_is_resistance(self):
        for line in self:
            line.is_resistance = self._is_plat_resistance(line.plat_type_id.name)

    # ── ONCHANGE ─────────────────────────────────────────────────────────

    @api.onchange('plat_type_id')
    def _onchange_plat_type_id(self):
        """Effacer la catégorie de menu si le type n'est pas un plat de résistance."""
        if not self._is_plat_resistance(self.plat_type_id.name) and self.menu_category_id:
            self.menu_category_id = False

    @api.onchange('plat_ids')
    def _onchange_plat_ids(self):
        """Auto-remplir la catégorie de menu depuis le premier plat sélectionné."""
        if self.is_resistance and self.plat_ids and not self.menu_category_id:
            for plat in self.plat_ids:
                if plat.menu_category_id:
                    self.menu_category_id = plat.menu_category_id
                    break

    # ── CONTRAINTES ─────────────────────────────────────────────────────

    @api.constrains('plat_type_id', 'menu_category_id')
    def _check_menu_category_for_resistance_only(self):
        """La catégorie de menu ne peut être définie que pour les plats de résistance."""
        for line in self:
            if line.menu_category_id and not line.is_resistance:
                raise ValidationError(
                    _("La catégorie de menu ne peut être définie que pour les plats de résistance. "
                      "Veuillez effacer la catégorie pour les lignes de type Entrée ou Dessert.")
                )
