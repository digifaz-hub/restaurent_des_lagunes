/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useRef, onWillUnset } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

export class PriceHistoryChart extends Component {
    static template = "lagunes_market.PriceHistoryChart";
    
    setup() {
        this.chartRef = useRef("chart");
        this.chart = null;

        onWillStart(async () => {
            // S'assurer que Chart.js est chargé
            await loadJS("/web/static/lib/Chart/Chart.js");
        });

        onMounted(() => {
            this.renderChart();
        });

        onWillUnset(() => {
            if (this.chart) {
                this.chart.destroy();
            }
        });
    }

    renderChart() {
        if (!this.props.record.data.price_history_json) return;

        try {
            const data = JSON.parse(this.props.record.data.price_history_json);
            if (data.length === 0) return;

            const labels = data.map(d => d.date);
            const prices = data.map(d => d.price);

            const ctx = this.chartRef.el.getContext('2d');
            
            // Gradient pour l'effet premium
            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, 'rgba(22, 22, 109, 0.2)');
            gradient.addColorStop(1, 'rgba(22, 22, 109, 0.0)');

            this.chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Prix d\'achat (FCFA)',
                        data: prices,
                        borderColor: '#16166d',
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointBackgroundColor: '#ffffff',
                        pointBorderColor: '#16166d',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            backgroundColor: '#16166d',
                            titleFont: { size: 14, weight: 'bold' },
                            padding: 12,
                            cornerRadius: 8
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            grid: { color: 'rgba(0,0,0,0.05)' },
                            ticks: { font: { size: 11 } }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: { size: 10 } }
                        }
                    }
                }
            });
        } catch (e) {
            console.error("Erreur lors du rendu du graphique de prix:", e);
        }
    }
}

// Enregistrement du widget pour pouvoir l'utiliser dans le XML
registry.category("fields").add("lagunes_price_history_chart", {
    component: PriceHistoryChart,
    supportedTypes: ["text"],
});
