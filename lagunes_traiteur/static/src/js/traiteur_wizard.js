/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.TraiteurWizard = publicWidget.Widget.extend({
    selector: '#traiteur_form',
    disabledInEditableMode: false,

    events: {
        'click #next-step': '_onClickNext',
        'click #prev-step': '_onClickPrev',
        'change input[name="date_mode"]': '_onDateModeChange',
        'change input[name="niveau_id"]': '_onNiveauChange',
    },

    start() {
        console.log('[TraiteurWizard] start() - Widget actif');

        // Lecture donnees serveur
        this.constituantsData = {};
        const serverEl = document.getElementById('traiteur-server-data');
        if (serverEl) {
            try {
                this.constituantsData = JSON.parse(serverEl.getAttribute('data-constituants') || '{}');
                console.log('[TraiteurWizard] constituantsData OK:', Object.keys(this.constituantsData).length, 'niveaux');
            } catch(e) {
                console.error('[TraiteurWizard] Erreur JSON:', e);
            }
        }

        this.currentStep = 1;
        this.totalSteps  = 5;

        this._updateDateMode();
        this._updateStepUI();

        console.log('[TraiteurWizard] Pret.');
        return this._super(...arguments);
    },

    // ── Handlers evenements ────────────────────────────────────────────────────

    _onClickNext(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('[TraiteurWizard] Clic Suivant, etape:', this.currentStep);
        if (this._validateStep(this.currentStep) && this.currentStep < this.totalSteps) {
            this.currentStep++;
            this._updateStepUI();
        }
    },

    _onClickPrev(e) {
        e.preventDefault();
        e.stopPropagation();
        if (this.currentStep > 1) {
            this.currentStep--;
            this._updateStepUI();
        }
    },

    _onDateModeChange() {
        this._updateDateMode();
    },

    _onNiveauChange(e) {
        if (e.target.checked) {
            this._showConstituants(e.target.value);
        }
    },

    // ── UI ─────────────────────────────────────────────────────────────────────

    _updateStepUI() {
        const form = this.el;
        const currentStep = this.currentStep;

        form.querySelectorAll('.traiteur-step-content').forEach(el => el.classList.add('d-none'));
        const stepEl = form.querySelector('#step-' + currentStep);
        if (stepEl) stepEl.classList.remove('d-none');

        document.querySelectorAll('#traiteur-steps .nav-link').forEach(el => {
            const s = parseInt(el.getAttribute('data-step'), 10);
            el.classList.toggle('active', s === currentStep);
            el.classList.toggle('bg-light', s < currentStep);
        });

        const prevBtn = document.getElementById('prev-step');
        const nextBtn = document.getElementById('next-step');
        if (prevBtn) prevBtn.classList.toggle('d-none', currentStep === 1);
        if (currentStep === this.totalSteps) {
            if (nextBtn) nextBtn.classList.add('d-none');
            this._updateRecap();
        } else {
            if (nextBtn) nextBtn.classList.remove('d-none');
        }

        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    _updateDateMode() {
        const single = document.getElementById('date_mode_single');
        const isSingle = !single || single.checked;
        const sc = document.getElementById('date_single_container');
        const rc = document.getElementById('date_range_container');
        if (sc) sc.classList.toggle('d-none', !isSingle);
        if (rc) rc.classList.toggle('d-none', isSingle);
    },

    _showConstituants(niveauId) {
        const container = document.getElementById('constituants-container');
        const list = document.getElementById('constituants-list');
        if (!container || !list) return;
        const items = this.constituantsData[niveauId] || [];
        if (items.length > 0) {
            list.innerHTML = items.map(c =>
                `<div class="col-md-6"><div class="d-flex align-items-center gap-2 p-2 bg-light rounded">` +
                `<i class="fa fa-check-circle text-success"></i><span>${c}</span></div></div>`
            ).join('');
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    },

    _updateRecap() {
        const form = this.el;
        const recap = document.getElementById('recap-content');
        if (!recap) return;

        const types = Array.from(form.querySelectorAll('input[name="type_ids"]:checked'))
            .map(i => { const l = i.parentElement.querySelector('.h5'); return l ? l.textContent.trim() : ''; })
            .filter(Boolean);

        const niv = form.querySelector('input[name="niveau_id"]:checked');
        const nivLabel = niv ? niv.parentElement.querySelector('.h5') : null;
        const nivName  = nivLabel ? nivLabel.textContent.trim() : '-';

        const nbPersEl = form.querySelector('input[name="nb_personnes"]');
        const nbPers   = nbPersEl ? nbPersEl.value : '-';

        const single   = document.getElementById('date_mode_single');
        const isSingle = !single || single.checked;
        const ds = document.getElementById('date_single');
        const dr = document.getElementById('date_debut_range');
        const df = document.getElementById('date_fin_range');
        const dDebut = isSingle ? (ds ? ds.value : '') : (dr ? dr.value : '');
        const dFin   = isSingle ? dDebut : (df ? df.value : '');
        const dates  = dDebut === dFin ? dDebut : dDebut + ' au ' + dFin;

        recap.innerHTML =
            `<div class="mb-3"><small class="text-muted text-uppercase fw-bold">Types</small><div class="fw-bold">${types.join(', ') || 'Aucun'}</div></div>` +
            `<div class="mb-3"><small class="text-muted text-uppercase fw-bold">Formule</small><div class="fw-bold">${nivName}</div></div>` +
            `<div class="mb-3"><small class="text-muted text-uppercase fw-bold">Convives</small><div class="fw-bold">${nbPers} personnes</div></div>` +
            `<div class="mb-3"><small class="text-muted text-uppercase fw-bold">Dates</small><div class="fw-bold">${dates || '-'}</div></div>`;
    },

    // ── Modale & Toast Notifications ──────────────────────────────────────────
    
    _showErrorModal(message) {
        const modalEl = document.getElementById('errorModal');
        const messageEl = document.getElementById('errorModalMessage');
        if (modalEl && messageEl) {
            messageEl.textContent = message;
            // Utilisation de l'API native Bootstrap 5
            if (window.bootstrap && window.bootstrap.Modal) {
                const modal = new window.bootstrap.Modal(modalEl);
                modal.show();
            } else if ($.fn.modal) {
                $(modalEl).modal('show');
            }
        } else {
            // Fallback sur toast si modale non trouvee
            this._showToast(message, 'danger');
        }
    },

    _showToast(message, type = 'warning') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toastId = 'toast-' + Date.now();
        const icons = {
            success: 'fa-check-circle',
            danger: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        const colors = {
            success: 'text-success',
            danger: 'text-danger',
            warning: 'text-warning',
            info: 'text-info'
        };

        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center border-0 shadow-lg mb-2" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000">
                <div class="d-flex">
                    <div class="toast-body d-flex align-items-center gap-2">
                        <i class="fa ${icons[type]} ${colors[type]} fs-5"></i>
                        <span class="fw-medium">${message}</span>
                    </div>
                    <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', toastHTML);
        const toastEl = document.getElementById(toastId);

        // Animation d'entrée
        toastEl.style.transform = 'translateX(100%)';
        toastEl.style.opacity = '0';
        toastEl.style.transition = 'all 0.3s ease-out';

        requestAnimationFrame(() => {
            toastEl.style.transform = 'translateX(0)';
            toastEl.style.opacity = '1';
        });

        // Auto-suppression avec animation de sortie
        setTimeout(() => {
            toastEl.style.transform = 'translateX(100%)';
            toastEl.style.opacity = '0';
            setTimeout(() => toastEl.remove(), 300);
        }, 4000);
    },

    // ── Validation ─────────────────────────────────────────────────────────────

    _validateStep(step) {
        const el = this.el.querySelector('#step-' + step);
        if (!el) return true;

        if (step === 1) {
            const checked = el.querySelectorAll('input[name="type_ids"]:checked');
            if (checked.length === 0) {
                this._showErrorModal("Veuillez choisir au moins un type d'événement pour continuer.");
                return false;
            }
            return true;
        }

        if (step === 2) {
            if (!el.querySelector('input[name="niveau_id"]:checked')) {
                this._showErrorModal("Veuillez choisir une formule (Standard, Améliorée...) avant de passer à l'étape suivante.");
                return false;
            }
            const modeEl = el.querySelector('input[name="date_mode"]:checked');
            const mode   = modeEl ? modeEl.value : 'single';
            const ds = document.getElementById('date_single');
            const dr = document.getElementById('date_debut_range');
            const dateDebutVal = mode === 'single' ? (ds ? ds.value : '') : (dr ? dr.value : '');

            if (!dateDebutVal) {
                this._showErrorModal("La date de début est obligatoire.");
                return false;
            }
            const debut = new Date(dateDebutVal);
            const today = new Date(); today.setHours(0,0,0,0);
            if (debut < today) {
                this._showErrorModal("La date choisie ne peut pas être dans le passé.");
                return false;
            }

            if (mode === 'range') {
                const df = document.getElementById('date_fin_range');
                const finVal = df ? df.value : '';
                if (!finVal) {
                    this._showErrorModal("Veuillez renseigner la date de fin pour votre période.");
                    return false;
                }
                if (new Date(finVal) < debut) {
                    this._showErrorModal("La date de fin doit être postérieure à la date de début.");
                    return false;
                }
            }
            return true;
        }

        let valid = true;
        el.querySelectorAll('input[required], select[required], textarea[required]').forEach(input => {
            if (!input.checkValidity()) { 
                input.reportValidity(); 
                valid = false; 
            }
        });
        
        if (!valid) {
            this._showErrorModal("Certains champs obligatoires sont manquants ou incorrects. Veuillez les vérifier.");
        }
        
        return valid;
    },
});

export default publicWidget.registry.TraiteurWizard;