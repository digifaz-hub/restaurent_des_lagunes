# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class LagunesDashboard(models.TransientModel):
    """
    Modèle TransientModel pour le dashboard de la cantine.
    Ne persiste pas en base — toutes les données sont calculées à la volée.
    """
    _name = 'lagunes.dashboard'
    _description = 'Tableau de bord Cantine'

    # ── KPI Employés ────────────────────────────────────────────────────
    employe_total = fields.Integer(
        string='Employés actifs',
        compute='_compute_employe_kpis',
    )
    employe_new_month = fields.Integer(
        string='Nouvelles inscriptions ce mois',
        compute='_compute_employe_kpis',
    )
    entreprise_total = fields.Integer(
        string='Entreprises clientes',
        compute='_compute_employe_kpis',
    )

    # ── KPI Commandes ───────────────────────────────────────────────────
    commande_today = fields.Integer(
        string="Commandes du jour",
        compute='_compute_commande_kpis',
    )
    commande_today_confirmed = fields.Integer(
        string="Confirmées",
        compute='_compute_commande_kpis',
    )
    commande_today_preparing = fields.Integer(
        string="En préparation",
        compute='_compute_commande_kpis',
    )
    commande_today_ready = fields.Integer(
        string="Prêtes",
        compute='_compute_commande_kpis',
    )
    commande_today_delivered = fields.Integer(
        string="Livrées",
        compute='_compute_commande_kpis',
    )
    commande_today_cancelled = fields.Integer(
        string="Annulées",
        compute='_compute_commande_kpis',
    )
    commande_yesterday = fields.Integer(
        string="Commandes hier",
        compute='_compute_commande_kpis',
    )
    commande_week = fields.Integer(
        string="Commandes cette semaine",
        compute='_compute_commande_kpis',
    )
    commande_month = fields.Integer(
        string="Commandes ce mois",
        compute='_compute_commande_kpis',
    )
    # ratio vs hier (int, %)
    commande_delta_pct = fields.Integer(
        string="Variation vs hier (%)",
        compute='_compute_commande_kpis',
    )

    # ── KPI Menus ───────────────────────────────────────────────────────
    plat_total = fields.Integer(
        string="Plats actifs",
        compute='_compute_menu_kpis',
    )
    week_menu_published = fields.Boolean(
        string="Menu de la semaine publié",
        compute='_compute_menu_kpis',
    )
    week_menu_name = fields.Char(
        string="Nom du menu actif",
        compute='_compute_menu_kpis',
    )
    plat_type_total = fields.Integer(
        string="Types de plats",
        compute='_compute_menu_kpis',
    )

    # ── KPI Facturation ─────────────────────────────────────────────────
    facturation_draft = fields.Integer(
        string="Périodes en brouillon",
        compute='_compute_facturation_kpis',
    )
    facturation_confirmed = fields.Integer(
        string="Périodes confirmées",
        compute='_compute_facturation_kpis',
    )
    commande_not_invoiced = fields.Integer(
        string="Commandes non facturées",
        compute='_compute_facturation_kpis',
    )

    # ── KPI Stock Marché ────────────────────────────────────────────────
    commande_stock_insufficient = fields.Integer(
        string="Commandes stock insuffisant",
        compute='_compute_stock_kpis',
        help="Nombre de commandes avec stock insuffisant non résolu",
    )
    commande_stock_insufficient_today = fields.Integer(
        string="Stock insuffisant aujourd'hui",
        compute='_compute_stock_kpis',
        help="Commandes du jour avec stock insuffisant",
    )
    stock_alerts_json = fields.Text(
        string="Alertes stock (JSON)",
        compute='_compute_stock_kpis',
        help="Liste des alertes stock pour affichage dashboard",
    )

    # ── Activité récente (JSON serialisé) ───────────────────────────────
    recent_activity_json = fields.Text(
        string="Activité récente (JSON)",
        compute='_compute_recent_activity',
    )

    # ── Top entreprises semaine (JSON) ──────────────────────────────────
    top_entreprises_json = fields.Text(
        string="Top entreprises (JSON)",
        compute='_compute_top_entreprises',
    )

    # ── Sparkline 7 jours (JSON) ────────────────────────────────────────
    sparkline_json = fields.Text(
        string="Sparkline 7 jours (JSON)",
        compute='_compute_sparkline',
    )

    # ── Nouveaux Indicateurs Premium ──────────────────────────────────
    penetration_rate = fields.Float(
        string="Taux de fréquentation (%)",
        compute='_compute_premium_indicators',
    )
    tomorrow_forecast = fields.Integer(
        string="Prévisionnel J+1",
        compute='_compute_premium_indicators',
    )
    top_profitability_json = fields.Text(
        string="Top Rentabilité (JSON)",
        compute='_compute_premium_indicators',
    )

    # ── Dernières commandes (JSON) ──────────────────────────────────────
    last_orders_json = fields.Text(
        string="Dernières commandes (JSON)",
        compute='_compute_recent_activity',
    )

    # ════════════════════════════════════════════════════════════════════
    #  COMPUTE STOCK KPIs
    # ════════════════════════════════════════════════════════════════════

    @api.depends()
    def _compute_stock_kpis(self):
        """Calcule les KPIs liés au stock marché et commandes"""
        for rec in self:
            company_id = self.env.company.id
            today = date.today()

            # Commandes avec stock insuffisant (toutes périodes)
            rec.commande_stock_insufficient = self.env['lagunes.commande'].search_count([
                ('stock_insufficient', '=', True),
                ('state', 'not in', ['delivered', 'cancelled']),
                ('company_id', '=', company_id),
            ])

            # Commandes stock insuffisant du jour
            rec.commande_stock_insufficient_today = self.env['lagunes.commande'].search_count([
                ('stock_insufficient', '=', True),
                ('date', '=', today),
                ('state', 'not in', ['delivered', 'cancelled']),
                ('company_id', '=', company_id),
            ])

            # Préparer liste des alertes pour le dashboard
            alerts = []
            commandes_alert = self.env['lagunes.commande'].search([
                ('stock_insufficient', '=', True),
                ('state', 'not in', ['delivered', 'cancelled']),
                ('company_id', '=', company_id),
            ], order='stock_forced_date desc', limit=5)

            for cmd in commandes_alert:
                alerts.append({
                    'id': cmd.id,
                    'reference': cmd.reference,
                    'date': cmd.date.isoformat() if cmd.date else '',
                    'forced_by': cmd.stock_forced_by_id.name or 'Inconnu',
                    'forced_date': cmd.stock_forced_date.isoformat() if cmd.stock_forced_date else '',
                    'entreprise': cmd.entreprise_id.name or '',
                    'state': cmd.state,
                })

            rec.stock_alerts_json = json.dumps(alerts)

    # ════════════════════════════════════════════════════════════════════
    #  COMPUTE
    # ════════════════════════════════════════════════════════════════════

    @api.depends()
    def _compute_employe_kpis(self):
        for rec in self:
            company_id = self.env.company.id
            rec.employe_total = self.env['lagunes.employe'].search_count([
                ('active', '=', True),
                ('entreprise_id.company_id', '=', company_id),
            ])
            mois_debut = date.today().replace(day=1)
            rec.employe_new_month = self.env['lagunes.employe'].search_count([
                ('active', '=', True),
                ('date_inscription', '>=', mois_debut),
                ('entreprise_id.company_id', '=', company_id),
            ])
            rec.entreprise_total = self.env['res.partner'].search_count([
                ('is_cantine_client', '=', True),
                ('company_id', '=', company_id),
            ])

    @api.depends()
    def _compute_commande_kpis(self):
        for rec in self:
            company_id = self.env.company.id
            today = date.today()
            yesterday = today - timedelta(days=1)

            base = [('state', '!=', 'cancelled'), ('company_id', '=', company_id)]

            today_cmd = self.env['lagunes.commande'].search(
                base + [('date', '=', today)]
            )
            rec.commande_today = len(today_cmd)
            rec.commande_today_confirmed = len(
                today_cmd.filtered(lambda c: c.state == 'confirmed'))
            rec.commande_today_preparing = len(
                today_cmd.filtered(lambda c: c.state == 'preparing'))
            rec.commande_today_ready = len(
                today_cmd.filtered(lambda c: c.state == 'ready'))
            rec.commande_today_delivered = len(
                today_cmd.filtered(lambda c: c.state == 'delivered'))

            yesterday_count = self.env['lagunes.commande'].search_count(
                base + [('date', '=', yesterday)]
            )
            rec.commande_yesterday = yesterday_count

            if yesterday_count > 0:
                delta = int(
                    ((rec.commande_today - yesterday_count) / yesterday_count) * 100
                )
            else:
                delta = 0
            rec.commande_delta_pct = delta

            week_start = today - timedelta(days=today.weekday())
            rec.commande_week = self.env['lagunes.commande'].search_count(
                base + [('date', '>=', week_start), ('date', '<=', today)]
            )
            month_start = today.replace(day=1)
            rec.commande_month = self.env['lagunes.commande'].search_count(
                base + [('date', '>=', month_start), ('date', '<=', today)]
            )
            rec.commande_today_cancelled = self.env['lagunes.commande'].search_count(
                [('date', '=', today), ('state', '=', 'cancelled'), ('company_id', '=', company_id)]
            )

    @api.depends()
    def _compute_menu_kpis(self):
        for rec in self:
            company_id = self.env.company.id
            rec.plat_total = self.env['lagunes.plat'].search_count([
                ('active', '=', True),
                ('company_id', '=', company_id),
            ])
            rec.plat_type_total = self.env['lagunes.plat.type'].search_count([
                ('active', '=', True),
            ])

            # Chercher le menu de la semaine en cours (publié)
            today = date.today()
            days_since_saturday = (today.weekday() - 5) % 7
            week_start = today - timedelta(days=days_since_saturday)
            menu = self.env['lagunes.week.menu'].search([
                ('week_start_date', '=', week_start),
                ('state', '=', 'published'),
                ('active', '=', True),
                '|', ('is_global', '=', True),
                ('company_id', '=', company_id),
            ], limit=1)
            if not menu:
                menu = self.env['lagunes.week.menu'].search([
                    ('state', '=', 'published'),
                    ('active', '=', True),
                    '|', ('is_global', '=', True),
                    ('company_id', '=', company_id),
                ], order='week_start_date desc', limit=1)

            rec.week_menu_published = bool(menu)
            rec.week_menu_name = menu.name if menu else ''

    @api.depends()
    def _compute_facturation_kpis(self):
        for rec in self:
            company_id = self.env.company.id
            rec.facturation_draft = self.env[
                'lagunes.facturation.periode'].search_count(
                [('state', '=', 'draft'), ('company_id', '=', company_id)]
            )
            rec.facturation_confirmed = self.env[
                'lagunes.facturation.periode'].search_count(
                [('state', '=', 'confirmed'), ('company_id', '=', company_id)]
            )
            rec.commande_not_invoiced = self.env['lagunes.commande'].search_count(
                [('state', '=', 'delivered'), ('facturation_state', '=', 'not_invoiced'), ('company_id', '=', company_id)]
            )

    @api.depends()
    def _compute_recent_activity(self):
        for rec in self:
            company_id = self.env.company.id
            activities = []

            # 1. 5 dernières commandes (Créations)
            last_cmds = self.env['lagunes.commande'].search(
                [('company_id', '=', company_id)], order='create_date desc', limit=5)
            for cmd in last_cmds:
                minutes = 0
                if cmd.create_date:
                    diff = datetime.now() - cmd.create_date.replace(tzinfo=None)
                    minutes = int(diff.total_seconds() / 60)
                activities.append({
                    'type': 'commande',
                    'icon': 'fa-plus-circle',
                    'label': f"Nouvelle Commande — {cmd.employee_name or 'Employé'}",
                    'sub': f"{cmd.entreprise_id.name if cmd.entreprise_id else ''}",
                    'badge': cmd.reference or '',
                    'minutes': minutes,
                })

            # 2. 3 dernières commandes livrées
            delivered_cmds = self.env['lagunes.commande'].search(
                [('company_id', '=', company_id), ('state', '=', 'delivered')], 
                order='write_date desc', limit=3)
            for cmd in delivered_cmds:
                diff = datetime.now() - cmd.write_date.replace(tzinfo=None)
                activities.append({
                    'type': 'delivery',
                    'icon': 'fa-truck',
                    'label': f"Livrée — {cmd.employee_name}",
                    'sub': cmd.reference,
                    'badge': 'Succès',
                    'minutes': int(diff.total_seconds() / 60),
                })

            # 3. Dernières factures confirmées
            last_invoices = self.env['lagunes.facturation.periode'].search(
                [('company_id', '=', company_id), ('state', '=', 'confirmed')], 
                order='write_date desc', limit=2)
            for inv in last_invoices:
                diff = datetime.now() - inv.write_date.replace(tzinfo=None)
                activities.append({
                    'type': 'invoice',
                    'icon': 'fa-file-text-o',
                    'label': f"Facture Confirmée — {inv.entreprise_id.name}",
                    'sub': inv.name,
                    'badge': 'Finance',
                    'minutes': int(diff.total_seconds() / 60),
                })

            # 4. 3 derniers employés inscrits
            last_emp = self.env['lagunes.employe'].search(
                [('active', '=', True), ('company_id', '=', company_id)],
                order='id desc', limit=3)
            for emp in last_emp:
                minutes = 9999
                if emp.create_date:
                    diff = datetime.now() - emp.create_date.replace(tzinfo=None)
                    minutes = int(diff.total_seconds() / 60)
                activities.append({
                    'type': 'employe',
                    'icon': 'fa-user-plus',
                    'label': f"Inscription — {emp.display_name_full}",
                    'sub': emp.entreprise_id.name if emp.entreprise_id else '',
                    'badge': 'Employé',
                    'minutes': minutes,
                })

            activities.sort(key=lambda x: x.get('minutes', 9999))
            rec.recent_activity_json = json.dumps(activities[:8])

            # Dernières commandes structurées pour le tableau
            orders_data = []
            for cmd in last_cmds:
                orders_data.append({
                    'id': cmd.id,
                    'reference': cmd.reference,
                    'employee': cmd.employee_name,
                    'plat': ' + '.join(filter(None, [
                        cmd.entree_plat_id.name if cmd.entree_plat_id else None,
                        cmd.resistance_plat_id.name if cmd.resistance_plat_id else None,
                        cmd.dessert_plat_id.name if cmd.dessert_plat_id else None
                    ])) or 'Menu complet',
                    'state': cmd.state,
                    'state_label': next((label for value, label in (cmd._fields['state'].selection or []) if value == cmd.state), cmd.state),
                })
            rec.last_orders_json = json.dumps(orders_data)

    @api.depends()
    def _compute_top_entreprises(self):
        for rec in self:
            company_id = self.env.company.id
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

            # Commandes par entreprise cette semaine
            cmds = self.env['lagunes.commande'].search([
                ('date', '>=', week_start),
                ('date', '<=', today),
                ('state', '!=', 'cancelled'),
                ('company_id', '=', company_id),
            ])
            entreprises = self.env['res.partner'].search([
                ('is_cantine_client', '=', True),
                ('company_id', '=', company_id),
            ])
            result = []
            max_count = 1
            for ent in entreprises:
                count = len(cmds.filtered(lambda c: c.entreprise_id == ent))
                if count > 0:
                    result.append({'name': ent.name, 'count': count})
                    if count > max_count:
                        max_count = count

            result.sort(key=lambda x: x['count'], reverse=True)
            for item in result:
                item['pct'] = int((item['count'] / max_count) * 100)

            rec.top_entreprises_json = json.dumps(result[:6])

    @api.depends()
    def _compute_sparkline(self):
        for rec in self:
            company_id = self.env.company.id
            today = date.today()
            data = []
            for i in range(6, -1, -1):
                d = today - timedelta(days=i)
                count = self.env['lagunes.commande'].search_count([
                    ('date', '=', d),
                    ('state', '!=', 'cancelled'),
                    ('company_id', '=', company_id),
                ])
                data.append({
                    'date': d.strftime('%d/%m'),
                    'count': count,
                })
            rec.sparkline_json = json.dumps(data)

    def _compute_premium_indicators(self):
        """Calcule les indicateurs Premium (Fréquentation, Prévisionnel, Rentabilité)"""
        company_id = self.env.company.id
        today = date.today()
        
        for rec in self:
            # 1. Fréquentation
            total_headcount = sum(self.env['res.partner'].search([
                ('is_cantine_client', '=', True), ('company_id', '=', company_id)
            ]).mapped('total_headcount')) or 1
            today_orders = self.env['lagunes.commande'].search_count([
                ('date', '=', today), ('company_id', '=', company_id), ('state', '!=', 'cancelled')
            ])
            rec.penetration_rate = (today_orders / total_headcount) * 100

            # 2. Prévisionnel J+1
            tomorrow = today + timedelta(days=1)
            rec.tomorrow_forecast = self.env['lagunes.commande'].search_count([
                ('date', '=', tomorrow), ('company_id', '=', company_id), ('state', '!=', 'cancelled')
            ])

            # 3. Rentabilité (Top 5 Plats)
            top_plats = self.env['lagunes.plat'].search([
                ('company_id', '=', company_id), ('active', '=', True)
            ], order='margin_percent desc', limit=5)
            
            profit_data = []
            for p in top_plats:
                profit_data.append({
                    'name': p.name,
                    'margin': round(p.margin_percent, 1),
                    'price': p.prix_unitaire,
                })
            rec.top_profitability_json = json.dumps(profit_data)

    # ════════════════════════════════════════════════════════════════════
    #  MÉTHODE PRINCIPALE : retourne toutes les données en un seul appel
    # ════════════════════════════════════════════════════════════════════

    @api.model
    def get_dashboard_data(self):
        """
        Retourne toutes les données du dashboard en un seul appel RPC.
        Appelé par le composant OWL via /web/dataset/call_kw.
        """
        rec = self.create({})
        fields = [
            "employe_total", "employe_new_month", "entreprise_total",
            "commande_today", "commande_today_confirmed",
            "commande_today_preparing", "commande_today_delivered",
            "commande_today_cancelled", "commande_yesterday",
            "commande_week", "commande_month", "commande_delta_pct",
            "plat_total", "week_menu_published", "week_menu_name", "plat_type_total",
            "facturation_draft", "facturation_confirmed", "commande_not_invoiced",
            "recent_activity_json", "top_entreprises_json", "sparkline_json", "last_orders_json",
            "commande_today_ready",
            "commande_stock_insufficient", "commande_stock_insufficient_today", "stock_alerts_json",
            "penetration_rate", "tomorrow_forecast", "top_profitability_json",
        ]
        data = rec.read(fields)[0]
        return data

    # ════════════════════════════════════════════════════════════════════
    #  ACTIONS
    # ════════════════════════════════════════════════════════════════════

    def action_open_commandes_today(self):
        today = date.today()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Commandes du jour"),
            'res_model': 'lagunes.commande',
            'view_mode': 'list,kanban,form',
            'domain': [('date', '=', today)],
            'context': {'search_default_today': 1},
        }

    def action_open_employes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Employés"),
            'res_model': 'lagunes.employe',
            'view_mode': 'list,form',
            'domain': [('active', '=', True)],
        }

    def action_open_facturation(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Périodes de facturation"),
            'res_model': 'lagunes.facturation.periode',
            'view_mode': 'list,form',
        }

    def action_open_week_menu(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Menus hebdomadaires"),
            'res_model': 'lagunes.week.menu',
            'view_mode': 'list,form',
        }
