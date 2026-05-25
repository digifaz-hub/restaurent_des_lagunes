/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class MarketDashboard extends Component {
    static template = "lagunes_market.MarketDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: {
                kpis: {
                    total_articles: 0,
                    total_stock_value: 0,
                    monthly_expenses: 0,
                },
                recent_moves: [],
                top_consumed: [],
            },
            animated: {
                total_articles: 0,
                total_stock_value: 0,
                monthly_expenses: 0,
                rotation_index: 0,
            }
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        const data = await this.orm.call("lagunes.market.dashboard", "get_dashboard_data", [], {});
        this.state.data = data;
        this._animateCounters();
    }

    _animateCounters() {
        const duration = 1500;
        const keys = ['total_articles', 'total_stock_value', 'monthly_expenses', 'rotation_index'];
        keys.forEach(key => {
            const endValue = this.state.data.kpis[key] || 0;
            if (endValue === 0) return;
            let startTimestamp = null;
            const step = (timestamp) => {
                if (!startTimestamp) startTimestamp = timestamp;
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                this.state.animated[key] = Math.floor(progress * endValue);
                if (progress < 1) window.requestAnimationFrame(step);
            };
            window.requestAnimationFrame(step);
        });
    }

    formatCurrency(value) {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'XOF',
            minimumFractionDigits: 0,
        }).format(value);
    }

    formatDateShort(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
    }

    _openStockView() {
        this.action.doAction('lagunes_market.action_market_stock');
    }
}

registry.category("actions").add("market_dashboard_action", MarketDashboard);
