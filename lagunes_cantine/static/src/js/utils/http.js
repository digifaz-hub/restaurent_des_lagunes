/** @odoo-module **/

/**
 * Secure HTTP utilities for Lagunes Cantine
 * Handles CSRF tokens and secure JSON-RPC requests
 */

export class SecureHttp {
    /**
     * Get CSRF token from available sources
     * Priority: odoo.csrf_token > meta tag > input field
     * @returns {string} - CSRF token or empty string
     */
    static getCsrfToken() {
        // Priority 1: Global odoo object (set by Odoo web layout)
        if (typeof odoo !== 'undefined' && odoo.csrf_token) {
            return odoo.csrf_token;
        }

        // Priority 2: Meta tag
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.content || '';
        }

        // Priority 3: Input field
        const inputToken = document.querySelector('input[name="csrf_token"]');
        if (inputToken) {
            return inputToken.value || '';
        }

        console.warn('CSRF token not found');
        return '';
    }

    /**
     * Perform a secure JSON-RPC fetch request
     * @param {string} url - Endpoint URL
     * @param {Object} params - Request parameters
     * @param {string} method - HTTP method (default: 'POST')
     * @returns {Promise<Object>} - Response data
     * @throws {Error} - On HTTP or RPC errors
     */
    static async fetchJson(url, params = {}, method = 'POST') {
        const csrfToken = this.getCsrfToken();

        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        };

        if (csrfToken) {
            headers['X-CSRF-Token'] = csrfToken;
        }

        const body = JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: params,
            id: Math.floor(Math.random() * 1000000000),
        });

        try {
            const response = await fetch(url, {
                method,
                headers,
                body,
                credentials: 'same-origin',
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error.message || data.error.data?.message || 'Server error');
            }

            return data.result || {};
        } catch (err) {
            console.error('SecureHttp.fetchJson error:', err);
            throw err;
        }
    }

    /**
     * Perform a secure POST request with JSON body
     * @param {string} url - Endpoint URL
     * @param {Object} params - Request body
     * @returns {Promise<Object>} - Response data
     */
    static async post(url, params = {}) {
        return this.fetchJson(url, params, 'POST');
    }

    /**
     * Check if the application is online
     * @returns {boolean}
     */
    static isOnline() {
        return navigator.onLine;
    }
}
