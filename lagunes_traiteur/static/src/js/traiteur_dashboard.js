/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";

export class TraiteurDashboard extends Component {
    // Doit correspondre exactement au t-name dans traiteur_dashboard_templates.xml
    static template = "lagunes_traiteur.TraiteurDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            data: {
                kpis: {
                    new_demands: 0,
                    ongoing_prestas: 0,
                    ca_mensuel: "0",
                    conversion_rate: 0,
                },
                timeline: [],
                chart_data: "{}",
                revenue_chart_data: "{}",
            },
            animated: {
                new_demands: 0,
                ongoing_prestas: 0,
                conversion_rate: 0,
            },
        });

        // t-ref dans le XML — même convention que le market
        this.traiteurTypeChartRef = useRef("traiteurTypeChart");
        this.traiteurRevenueChartRef = useRef("traiteurRevenueChart");

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            this._renderCharts();
        });
    }

    async loadData() {
        const data = await this.orm.call(
            "lagunes.traiteur.dashboard",
            "get_dashboard_data",
            [],
            {}
        );
        this.state.data = data;
        this._animateCounters();
    }

    _animateCounters() {
        const duration = 1500;
        const keys = ["new_demands", "ongoing_prestas", "conversion_rate"];
        keys.forEach((key) => {
            const endValue = Number(this.state.data.kpis[key]) || 0;
            if (endValue === 0) {
                this.state.animated[key] = 0;
                return;
            }
            let startTimestamp = null;
            const step = (timestamp) => {
                if (!startTimestamp) startTimestamp = timestamp;
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                this.state.animated[key] = Math.floor(progress * endValue);
                if (progress < 1) window.requestAnimationFrame(step);
                else this.state.animated[key] = endValue;
            };
            window.requestAnimationFrame(step);
        });
    }

    _renderCharts() {
        if (typeof Chart === "undefined") return;
        this._renderRevenueChart();
        this._renderTypeChart();
    }

    _renderTypeChart() {
        const canvas = this.traiteurTypeChartRef.el;
        if (!canvas) return;
        try {
            const rawData = JSON.parse(this.state.data.chart_data || "{}");
            if (!rawData.labels || !rawData.datasets) return;
            new Chart(canvas.getContext("2d"), {
                type: "doughnut",
                data: rawData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: "bottom" } },
                },
            });
        } catch (e) {
            console.warn("[TraiteurDashboard] Chart type error:", e);
        }
    }

    _renderRevenueChart() {
        const canvas = this.traiteurRevenueChartRef.el;
        if (!canvas) return;
        try {
            const rawData = JSON.parse(this.state.data.revenue_chart_data || "{}");
            if (!rawData.labels || !rawData.datasets) return;
            new Chart(canvas.getContext("2d"), {
                type: "bar",
                data: rawData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } },
                },
            });
        } catch (e) {
            console.warn("[TraiteurDashboard] Chart revenue error:", e);
        }
    }

    _openAction(actionXmlId) {
        this.actionService.doAction(actionXmlId);
    }
}


// Même pattern que le market : registry.category("actions").add(tag, Composant)
registry.category("actions").add("lagunes_traiteur_dashboard_tag", TraiteurDashboard);