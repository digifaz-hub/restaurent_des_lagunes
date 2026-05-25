/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

class LagunesDashboard extends Component {
    static template = "lagunes_cantine.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        // État réactif du dashboard
        this.state = useState({
            loaded: false,
            error: false,
            data: {},
            animated: {
                commande_today: 0,
                commande_today_preparing: 0,
                commande_today_ready: 0,
                entreprise_total: 0,
                penetration_rate: 0,
                tomorrow_forecast: 0,
            },
            charts: {
                bar: null,
                line: null,
            }
        });

        // Références aux canvas pour Chart.js
        this.chartBarRef = useRef("chart_commandes");
        this.chartSparkRef = useRef("chart_sparkline");

        onMounted(async () => {
            // S'assurer que Chart.js est chargé (Odoo 18 l'inclut normalement)
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this._load();
        });

        onWillUnmount(() => {
            this._destroyCharts();
        });
    }

    // ─── Chargement des données ─────────────────────────────────────────
    async _load() {
        this.state.loaded = false;
        try {
            const result = await this.orm.call("lagunes.dashboard", "get_dashboard_data", [], {});
            this.state.data = result || {};
            this.state.loaded = true;
            this.state.error = false;
            
            // Lancer les animations
            this._animateCounters();

            // Attendre le prochain cycle de rendu pour que les canvas soient présents
            await new Promise(r => setTimeout(r, 0));
            this._renderCharts();
        } catch (e) {
            console.warn("Fallback to full read due to missing get_dashboard_data method");
            try {
                const data = await this._loadFallback();
                this.state.data = data;
                this.state.loaded = true;
                await new Promise(r => setTimeout(r, 0));
                this._renderCharts();
            } catch (err) {
                this.state.error = "Impossible de charger les données du dashboard.";
                console.error("Dashboard error:", err);
            }
        }
    }

    async _loadFallback() {
        const id = await this.orm.call("lagunes.dashboard", "create", [{}]);
        const fields = [
            "employe_total", "employe_new_month", "entreprise_total",
            "commande_today", "commande_today_confirmed",
            "commande_today_preparing", "commande_today_ready", "commande_today_delivered",
            "commande_today_cancelled", "commande_yesterday",
            "commande_week", "commande_month", "commande_delta_pct",
            "plat_total", "week_menu_published", "week_menu_name", "plat_type_total",
            "facturation_draft", "facturation_confirmed", "commande_not_invoiced",
            "recent_activity_json", "top_entreprises_json", "sparkline_json", "last_orders_json",
            "commande_stock_insufficient", "commande_stock_insufficient_today", "stock_alerts_json"
        ];
        const records = await this.orm.call("lagunes.dashboard", "read", [[id], fields]);
        return records[0] || {};
    }

    _animateCounters() {
        const duration = 1500; // 1.5s
        const keys = [
            'commande_today', 'commande_today_preparing', 'commande_today_ready', 
            'entreprise_total', 'penetration_rate', 'tomorrow_forecast'
        ];
        
        keys.forEach(key => {
            const endValue = this.state.data[key] || 0;
            if (endValue === 0) return;
            
            let startTimestamp = null;
            const step = (timestamp) => {
                if (!startTimestamp) startTimestamp = timestamp;
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                this.state.animated[key] = Math.floor(progress * endValue);
                if (progress < 1) {
                    window.requestAnimationFrame(step);
                }
            };
            window.requestAnimationFrame(step);
        });
    }

    // ─── Gestion des Graphiques (Chart.js) ──────────────────────────────
    _renderCharts() {
        this._destroyCharts();

        // 1. Graphique des Commandes par Entreprise
        if (this.chartBarRef.el) {
            const ctx = this.chartBarRef.el.getContext('2d');
            let rawData;
            try { rawData = JSON.parse(this.state.data.top_entreprises_json || "[]"); } catch { rawData = []; }
            
            this.state.charts.bar = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: rawData.map(d => d.name),
                    datasets: [{
                        label: 'Commandes',
                        data: rawData.map(d => d.count),
                        backgroundColor: (context) => {
                            const chart = context.chart;
                            const {ctx, chartArea} = chart;
                            if (!chartArea) return null;
                            const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                            gradient.addColorStop(0, '#16166d');
                            gradient.addColorStop(1, '#3b3bff');
                            return gradient;
                        },
                        borderRadius: 8,
                        hoverBackgroundColor: '#E65A2B',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { 
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#1a202c',
                            padding: 12,
                            titleFont: { size: 14, weight: 'bold' },
                            cornerRadius: 8,
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: true, 
                            grid: { color: '#edf2f7', drawBorder: false },
                            ticks: { font: { size: 11 } }
                        },
                        x: { 
                            grid: { display: false },
                            ticks: { font: { size: 11, weight: '600' } }
                        }
                    },
                    animation: { duration: 2000, easing: 'easeOutQuart' }
                }
            });
        }

        // 2. Sparkline / Évolution
        if (this.chartSparkRef.el) {
            const ctx = this.chartSparkRef.el.getContext('2d');
            let rawData;
            try { rawData = JSON.parse(this.state.data.sparkline_json || "[]"); } catch { rawData = []; }

            this.state.charts.line = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: rawData.map(d => d.date),
                    datasets: [{
                        label: 'Volume',
                        data: rawData.map(d => d.count),
                        borderColor: '#E65A2B',
                        backgroundColor: 'rgba(230, 90, 43, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 0,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: { display: false }
                    }
                }
            });
        }
    }

    _destroyCharts() {
        if (this.state.charts.bar) this.state.charts.bar.destroy();
        if (this.state.charts.line) this.state.charts.line.destroy();
    }

    // ─── Helpers Template ───────────────────────────────────────────────
    get lastOrders() {
        try {
            const json = this.state.data.last_orders_json;
            if (json) return JSON.parse(json);
            return this.state.data.last_orders || [];
        } catch { return []; }
    }

    get recentActivity() {
        try { return JSON.parse(this.state.data.recent_activity_json || "[]"); } catch { return []; }
    }

    get stockAlerts() {
        try { return JSON.parse(this.state.data.stock_alerts_json || "[]"); } catch { return []; }
    }

    get topProfitability() {
        try { return JSON.parse(this.state.data.top_profitability_json || "[]"); } catch { return []; }
    }

    formatTime(act) {
        const minutes = act.minutes || 0;

        // Pour les employés : Aujourd'hui / Hier
        if (act.type === 'employe') {
            if (minutes < 1440) return "Aujourd'hui";
            if (minutes < 2880) return "Hier";
            return "Ancien";
        }

        // Pour les commandes : À l'instant / X min / Xh Xm
        if (minutes < 1) return "À l'instant";
        if (minutes < 60) return `${minutes} min`;
        return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
    }

    formatDateShort(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
    }

    _onRefresh() {
        this._load();
    }

    _openAction(actionXmlId) {
        this.action.doAction(actionXmlId);
    }
}

registry.category("actions").add("lagunes_cantine.Dashboard", LagunesDashboard);

export default LagunesDashboard;
