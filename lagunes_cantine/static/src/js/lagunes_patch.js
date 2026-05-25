/** @odoo-module **/

/**
 * lagunes_patch.js — Odoo 18
 *
 * Gère la classe CSS `lagunes-active` sur le <body> via le
 * router d'Odoo 18, sans patcher ActionContainer.
 *
 * Odoo 18 expose un service `router` et un bus d'événements
 * sur lequel on peut écouter les changements d'action.
 * C'est l'API publique stable recommandée.
 */

import { registry } from "@web/core/registry";

// ----------------------------------------------------------------
// Modèles strictement propres au module lagunes_cantine.
// res.partner, sale.order, account.move → exclus.
// ----------------------------------------------------------------
const LAGUNES_MODELS = new Set([
    "lagunes.commande",
    "lagunes.week.menu",
    "lagunes.menu.category",
    "lagunes.plat",
    "lagunes.plat.option",
    "lagunes.facturation.periode",
    "lagunes.employe",
]);

const LAGUNES_CLASS = "lagunes-active";

function setLagunesActive(active) {
    document.body.classList.toggle(LAGUNES_CLASS, active);
}

function isLagunesAction(action) {
    if (!action) return false;
    if (action.type !== "ir.actions.act_window") return false;
    return LAGUNES_MODELS.has(action.res_model);
}

// ----------------------------------------------------------------
// Service Odoo 18 : s'enregistre dans la catégorie "services"
// et écoute le bus d'actions via env.bus ou action service.
// ----------------------------------------------------------------
const lagunesActiveService = {
    dependencies: ["action"],

    start(env, { action: actionService }) {
        // Écouter chaque changement d'action via le bus global d'Odoo
        env.bus.addEventListener("ACTION_MANAGER:UPDATE", ({ detail }) => {
            const currentAction = detail?.action;
            setLagunesActive(isLagunesAction(currentAction));
        });

        // Vérification initiale au démarrage
        const current = actionService.currentController?.action;
        setLagunesActive(isLagunesAction(current));

        return {};
    },
};

registry.category("services").add("lagunes_active_service", lagunesActiveService);