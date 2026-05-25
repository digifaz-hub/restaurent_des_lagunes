# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta

class LagunesMarketDashboard(models.TransientModel):
    _name = 'lagunes.market.dashboard'
    _description = 'Tableau de bord Marché'

    @api.model
    def get_dashboard_data(self):
        """Récupère les KPIs et données pour le tableau de bord Marché"""
        today = fields.Date.context_today(self)
        
        # 1. KPIs
        total_articles = self.env['lagunes.market.article'].search_count([])
        
        # Valeur totale théorique du stock (basé sur le dernier prix d'achat)
        total_stock_value = 0.0
        stocks = self.env['lagunes.market.stock'].search([('qty', '>', 0)])
        for stock in stocks:
            # Chercher le dernier prix d'achat validé pour cet article
            last_purchase = self.env['lagunes.market.line'].search([
                ('article_id', '=', stock.article_id.id),
                ('market_id.state', '=', 'validated')
            ], order='create_date desc', limit=1)
            
            if last_purchase:
                total_stock_value += stock.qty * last_purchase.unit_price

        # Dépenses du mois en cours
        first_day_month = today.replace(day=1)
        monthly_expenses = sum(self.env['lagunes.market'].search([
            ('date', '>=', first_day_month),
            ('state', '=', 'validated')
        ]).mapped('amount_total'))

        # 2. Derniers mouvements (pour la timeline)
        recent_moves = []
        moves = self.env['lagunes.market.stock.move'].search([], order='create_date desc', limit=10)
        for move in moves:
            recent_moves.append({
                'id': move.id,
                'date': move.create_date,
                'article': move.article_id.name,
                'qty': move.qty,
                'type': move.move_type,
                'note': move.note or '',
                'time_ago': self._get_time_ago(move.create_date)
            })

        # 3. Top articles consommés (sorties Cantine)
        top_consumed = []
        self.env.cr.execute("""
            SELECT a.name, SUM(m.qty) as total_qty, u.name as uom
            FROM lagunes_market_stock_move m
            JOIN lagunes_market_article a ON m.article_id = a.id
            JOIN lagunes_market_uom u ON a.default_uom_id = u.id
            WHERE m.move_type = 'out'
            GROUP BY a.name, u.name
            ORDER BY total_qty DESC
            LIMIT 5
        """)
        for row in self.env.cr.fetchall():
            top_consumed.append({
                'name': row[0],
                'qty': row[1],
                'uom': row[2]
            })

        # 4. Alertes stock (faible et critique)
        stock_alerts = []
        low_stock_count = self.env['lagunes.market.stock'].search_count([
            ('stock_status', '=', 'low'),
            ('company_id', '=', self.env.company.id),
        ])
        critical_stock_count = self.env['lagunes.market.stock'].search_count([
            ('stock_status', '=', 'critical'),
            ('company_id', '=', self.env.company.id),
        ])

        # Détail des alertes
        alert_stocks = self.env['lagunes.market.stock'].search([
            ('stock_status', 'in', ['low', 'critical']),
            ('company_id', '=', self.env.company.id),
        ], order='stock_status desc, qty asc', limit=10)

        for stock in alert_stocks:
            stock_alerts.append({
                'id': stock.id,
                'article': stock.article_id.name,
                'category': stock.category_id.name or 'Non catégorisé',
                'qty': stock.qty,
                'uom': stock.uom,
                'reorder_point': stock.reorder_point,
                'status': stock.stock_status,
                'status_label': dict(stock._fields['stock_status']._description_selection(self.env)).get(stock.stock_status),
            })

        # 5. Mouvements de type déduction commande (Cantine)
        deduction_moves_cantine = self.env['lagunes.market.stock.move'].search([
            ('move_category', '=', 'order_deduction'),
            ('source', '=', 'cantine'),
            ('company_id', '=', self.env.company.id),
        ], order='date desc, id desc', limit=5)

        recent_deductions_cantine = []
        for move in deduction_moves_cantine:
            recent_deductions_cantine.append({
                'id': move.id,
                'date': move.date.isoformat() if move.date else '',
                'article': move.article_id.name,
                'qty': move.qty,
                'uom': move.uom,
                'reference': move.reference or '',
                'note': move.note or '',
                'plat': move.plat_name or '',
            })

        # 5b. Mouvements de type déduction commande (Traiteur)
        deduction_moves_traiteur = self.env['lagunes.market.stock.move'].search([
            ('move_category', '=', 'order_deduction'),
            ('source', '=', 'traiteur'),
            ('company_id', '=', self.env.company.id),
        ], order='date desc, id desc', limit=5)

        recent_deductions_traiteur = []
        for move in deduction_moves_traiteur:
            recent_deductions_traiteur.append({
                'id': move.id,
                'date': move.date.isoformat() if move.date else '',
                'article': move.article_id.name,
                'qty': move.qty,
                'uom': move.uom,
                'reference': move.reference or '',
                'note': move.note or '',
                'plat': move.plat_name or '',
            })

        # 6. Statistiques Analytiques (Rotation & Autonomie)
        last_30_days = today - timedelta(days=30)
        
        # Rotation moyenne (Simplified: Out qty / Current Stock)
        self.env.cr.execute("""
            SELECT COALESCE(SUM(qty), 0) FROM lagunes_market_stock_move 
            WHERE move_type = 'out' AND date >= %s
        """, (last_30_days,))
        total_out_30 = self.env.cr.fetchone()[0]
        total_stock_qty = sum(self.env['lagunes.market.stock'].search([]).mapped('qty')) or 1
        rotation_index = (total_out_30 / total_stock_qty) * 100

        # Autonomie moyenne (jours)
        # On calcule la conso journalière moyenne par article sur 30j
        avg_autonomy = 0
        monitored_stocks = self.env['lagunes.market.stock'].search([('qty', '>', 0)], limit=50)
        autonomy_details = []
        for s in monitored_stocks:
            self.env.cr.execute("""
                SELECT COALESCE(SUM(qty), 0) / 30.0 FROM lagunes_market_stock_move 
                WHERE article_id = %s AND move_type = 'out' AND date >= %s
            """, (s.article_id.id, last_30_days))
            daily_avg = self.env.cr.fetchone()[0] or 0.1 #évite division par zéro
            days_left = s.qty / daily_avg
            if days_left < 30: # On ne suit que ce qui risque de manquer
                autonomy_details.append({
                    'article': s.article_id.name,
                    'days': round(days_left, 1),
                    'status': 'danger' if days_left < 3 else 'warning' if days_left < 7 else 'info'
                })
        
        # 7. Variations de prix (Top 5 hausses)
        self.env.cr.execute("""
            SELECT name, unit_price, avg_old
            FROM (
                SELECT a.name, l.unit_price, 
                (SELECT AVG(unit_price) FROM lagunes_market_line l2 
                 JOIN lagunes_market m2 ON l2.market_id = m2.id 
                 WHERE l2.article_id = a.id AND m2.state = 'validated' AND m2.date < %s) as avg_old
                FROM lagunes_market_line l
                JOIN lagunes_market m ON l.market_id = m.id
                JOIN lagunes_market_article a ON l.article_id = a.id
                WHERE m.state = 'validated' AND m.date >= %s
            ) sub
            ORDER BY (unit_price - avg_old) DESC NULLS LAST
            LIMIT 5
        """, (last_30_days, last_30_days))
        price_variations = []
        for row in self.env.cr.fetchall():
            if row[2] and row[1] > row[2]:
                var_pct = ((row[1] - row[2]) / row[2]) * 100
                price_variations.append({
                    'name': row[0],
                    'current': row[1],
                    'old_avg': round(row[2], 2),
                    'pct': round(var_pct, 1)
                })

        return {
            'kpis': {
                'total_articles': total_articles,
                'total_stock_value': total_stock_value,
                'monthly_expenses': monthly_expenses,
                'low_stock_count': low_stock_count,
                'critical_stock_count': critical_stock_count,
                'rotation_index': round(rotation_index, 1),
            },
            'recent_moves': recent_moves,
            'top_consumed': top_consumed,
            'stock_alerts': stock_alerts,
            'recent_deductions_cantine': recent_deductions_cantine,
            'recent_deductions_traiteur': recent_deductions_traiteur,
            'autonomy_details': autonomy_details[:5],
            'price_variations': price_variations,
        }

    def _get_time_ago(self, dt):
        if not dt:
            return ""
        diff = datetime.now() - dt
        if diff.days > 0:
            if diff.days == 1:
                return _("Hier")
            return _("Il y a %s jours") % diff.days
        
        minutes = int(diff.seconds / 60)
        if minutes < 60:
            return _("Il y a %s min") % minutes
        
        hours = int(minutes / 60)
        return _("Il y a %s h") % hours
