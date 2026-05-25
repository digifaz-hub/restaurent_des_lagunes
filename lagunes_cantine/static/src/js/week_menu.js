/** @odoo-module **/

import { SecureHttp } from './utils/http.js';

function initWizard() {
    const wizardEl = document.getElementById('cantine-wizard');
    if (!wizardEl) return;
    if (wizardEl.dataset.wizardInited === '1') return;
    wizardEl.dataset.wizardInited = '1';

    // --- State ---
    let state = {
        currentStep: 1,
        selectedMain: null, // {id, name, options: []}
        selectedSides: [], // [{id, name, type}]
        selectedOptions: [], // [id]
        notes: '',
        orderForOther: false,
        orderForOtherName: '',
        entrepriseId: parseInt(wizardEl.dataset.entrepriseId) || 0,
        weekMenuId: parseInt(wizardEl.dataset.weekMenuId) || 0,
        selectedDay: parseInt(wizardEl.dataset.todayDay) || 0,
        peutPourAutres: wizardEl.dataset.peutPourAutres === 'true'
    };

    // --- Selectors ---
    const steps = document.querySelectorAll('.wizard-step');
    const progressSteps = document.querySelectorAll('.progress-step');
    const btnNext = document.querySelectorAll('.btn-next-step');
    const btnPrev = document.querySelectorAll('.btn-prev-step');
    const optionsContainer = document.getElementById('plat-options-container');
    const sidesCountBadge = document.getElementById('sides-count');
    const recapDetails = document.getElementById('wizard-recap-details');
    const btnFinalSubmit = document.getElementById('btn-final-submit');
    const feedbackEl = document.getElementById('wizard-feedback');

    // --- Functions ---

    function updateUI() {
        // Update Steps Visibility
        steps.forEach((step, idx) => {
            step.classList.toggle('active', (idx + 1) === state.currentStep);
        });

        // Update Progress Bar
        progressSteps.forEach((ps, idx) => {
            const stepNum = idx + 1;
            ps.classList.toggle('active', stepNum === state.currentStep);
            ps.classList.toggle('completed', stepNum < state.currentStep);
        });

        // Validation for Step 1 : plat de résistance obligatoire
        if (state.currentStep === 1) {
            const btnStep1 = document.querySelector('#step-1 .btn-next-step');
            if (btnStep1) btnStep1.disabled = !state.selectedMain;
        }

        if (state.currentStep === 3) {
            renderRecap();
        }

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function renderOptions() {
        if (!optionsContainer) return;
        const options = state.selectedMain ? state.selectedMain.options : [];
        
        if (options.length === 0) {
            optionsContainer.innerHTML = '<div class="alert alert-light border-0 text-center py-4">Aucune option particulière pour ce plat.</div>';
            return;
        }

        let html = '<div class="row g-3">';
        options.forEach(opt => {
            const isChecked = state.selectedOptions.includes(opt.id);
            html += `
                <div class="col-md-6">
                    <div class="option-card p-3 border rounded-lg d-flex align-items-center cursor-pointer ${isChecked ? 'bg-primary-light border-primary' : 'bg-white'}" data-option-id="${opt.id}">
                        <div class="form-check mb-0">
                            <input class="form-check-input" type="checkbox" ${isChecked ? 'checked' : ''}>
                            <label class="form-check-label fw-semibold ms-2">${opt.name}</label>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        optionsContainer.innerHTML = html;

        // Bind clicks
        optionsContainer.querySelectorAll('.option-card').forEach(card => {
            card.addEventListener('click', function() {
                const optId = parseInt(this.dataset.optionId);
                const idx = state.selectedOptions.indexOf(optId);
                if (idx > -1) {
                    state.selectedOptions.splice(idx, 1);
                } else {
                    state.selectedOptions.push(optId);
                }
                renderOptions();
            });
        });
    }

    function renderRecap() {
        if (!recapDetails) return;
        
        let sidesHtml = state.selectedSides.map(s => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="small text-muted">${s.type === 'entree' ? 'Entrée' : 'Dessert'}</span>
                <span class="fw-bold">${s.name}</span>
            </div>
        `).join('');

        const optionsNames = (state.selectedMain.options || [])
            .filter(o => state.selectedOptions.includes(o.id))
            .map(o => o.name);

        const entrees = state.selectedSides.filter(s => s.type === 'entree');
        const desserts = state.selectedSides.filter(s => s.type === 'dessert');

        recapDetails.innerHTML = `
            ${entrees.length > 0 ? `
                <div class="mb-3">
                    <div class="small text-uppercase fw-bold mb-1" style="letter-spacing:1px; font-size:10px; color:#28a745;">ENTRÉE</div>
                    ${entrees.map(s => `<div class="fw-bold">${s.name}</div>`).join('')}
                </div>
                <hr class="my-3 opacity-25"/>
            ` : ''}
            <div class="mb-3">
                <div class="small text-uppercase fw-bold mb-1" style="letter-spacing:1px; font-size:10px; color:#16166d;">PLAT DE RÉSISTANCE</div>
                <div class="h5 fw-bold" style="color: #16166d;">${state.selectedMain.name}</div>
                ${optionsNames.length > 0 ? `<div class="mt-2"><span class="badge" style="background:#e8e9f5; color:#16166d;"> + ${optionsNames.join(', ')}</span></div>` : ''}
            </div>
            ${desserts.length > 0 ? `
                <hr class="my-3 opacity-25"/>
                <div class="mb-3">
                    <div class="small text-uppercase fw-bold mb-1" style="letter-spacing:1px; font-size:10px; color:#fd7e14;">DESSERT</div>
                    ${desserts.map(s => `<div class="fw-bold">${s.name}</div>`).join('')}
                </div>
            ` : ''}
            ${state.notes ? `
                <div class="p-3 bg-light rounded mt-3">
                    <div class="small fw-bold text-muted mb-1">NOTES :</div>
                    <div class="small fst-italic">"${state.notes}"</div>
                </div>
            ` : ''}
        `;
    }

    function showFeedback(msg, type) {
        if (!feedbackEl) return;
        feedbackEl.className = 'mt-3 text-center alert alert-' + type;
        feedbackEl.textContent = msg;
        feedbackEl.classList.remove('d-none');
    }

    // --- Events ---

    // Step 1: Main course selection
    document.querySelectorAll('.plat-choice-card[data-type-role="resistance"]').forEach(card => {
        card.addEventListener('click', function() {
            document.querySelectorAll('.plat-choice-card[data-type-role="resistance"]').forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
            
            state.selectedMain = {
                id: parseInt(this.dataset.platId),
                name: this.dataset.platName,
                options: JSON.parse(this.dataset.options || '[]')
            };
            
            // Reset options if main changes
            state.selectedOptions = [];
            
            updateUI();
        });
    });

    // Step 1: Sides selection (entrée + dessert, max 2 combined)
    document.querySelectorAll('.side-choice-card').forEach(card => {
        card.addEventListener('click', function() {
            const platId = parseInt(this.dataset.platId);
            const typeRole = this.dataset.typeRole; // 'entree' or 'dessert'
            // Deduplicate by (id + type) so the same plat can fill different roles
            const idx = state.selectedSides.findIndex(s => s.id === platId && s.type === typeRole);

            if (idx > -1) {
                // Deselect
                state.selectedSides.splice(idx, 1);
                this.classList.remove('selected');
            } else {
                if (state.selectedSides.length < 2) {
                    state.selectedSides.push({
                        id: platId,
                        name: this.dataset.platName,
                        type: typeRole
                    });
                    this.classList.add('selected');
                }
            }

            if (sidesCountBadge) sidesCountBadge.textContent = state.selectedSides.length;
            updateUI();
        });
    });

    // Navigation
    btnNext.forEach(btn => {
        btn.addEventListener('click', () => {
            if (state.currentStep === 2) {
                state.notes = document.getElementById('wizard-notes').value;
            }
            state.currentStep++;
            if (state.currentStep === 2) renderOptions();
            updateUI();
        });
    });

    btnPrev.forEach(btn => {
        btn.addEventListener('click', () => {
            state.currentStep--;
            updateUI();
        });
    });

    // Other settings
    const otherCheck = document.getElementById('order-for-other-check');
    const otherInputWrap = document.getElementById('order-for-other-input');
    const otherNameInput = document.getElementById('order-for-other-name');

    if (otherCheck) {
        otherCheck.addEventListener('change', function() {
            state.orderForOther = this.checked;
            otherInputWrap.classList.toggle('d-none', !this.checked);
            if (this.checked) otherNameInput.focus();
        });
    }

    // Final Submit
    if (btnFinalSubmit) {
        btnFinalSubmit.addEventListener('click', function() {
            if (state.orderForOther) {
                state.orderForOtherName = otherNameInput.value.trim();
                if (!state.orderForOtherName) {
                    showFeedback('Veuillez entrer le nom du collègue.', 'warning');
                    return;
                }
            }

            btnFinalSubmit.disabled = true;
            btnFinalSubmit.innerHTML = '<i class="fa fa-spinner fa-spin me-2"/>ENVOI EN COURS...';

            const platsChoisis = {
                'resistance': state.selectedMain.id
            };
            // Envoie chaque side avec son type (entree/dessert) pour le backend
            state.selectedSides.forEach((side, idx) => {
                platsChoisis['side_' + idx] = side.id;
                platsChoisis['side_' + idx + '_type'] = side.type;
            });

            SecureHttp.fetchJson('/cantine/commander-semaine', {
                entreprise_id: state.entrepriseId,
                week_menu_id: state.weekMenuId,
                day: state.selectedDay,
                plats_choisis: platsChoisis,
                qty_entree: state.selectedSides.filter(s => s.type === 'entree').length,
                qty_dessert: state.selectedSides.filter(s => s.type === 'dessert').length,
                option_ids: state.selectedOptions,
                notes: state.notes,
                order_for_other: state.orderForOther,
                ordered_for_name: state.orderForOtherName,
                is_wizard: true // Flag to tell backend to handle 'side_X' keys
            }).then(result => {
                if (result.success) {
                    showFeedback('✓ ' + result.message, 'success');
                    btnFinalSubmit.innerHTML = 'COMMANDE RÉUSSIE !';
                    setTimeout(() => {
                        window.location.href = '/cantine/commandes/list';
                    }, 2000);
                } else {
                    showFeedback(result.message, 'danger');
                    btnFinalSubmit.disabled = false;
                    btnFinalSubmit.innerHTML = 'CONFIRMER ET COMMANDER';
                }
            }).catch(() => {
                showFeedback('Erreur de connexion.', 'danger');
                btnFinalSubmit.disabled = false;
                btnFinalSubmit.innerHTML = 'CONFIRMER ET COMMANDER';
            });
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWizard);
} else {
    initWizard();
}
