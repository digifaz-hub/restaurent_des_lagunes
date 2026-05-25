/** @odoo-module **/

/**
 * Validation utilities for Lagunes Cantine frontend
 * Secures user inputs against XSS and injection attacks
 */

export class InputValidator {
    /**
     * Validate an integer within a range
     * @param {any} value - Value to validate
     * @param {number} min - Minimum allowed value (default: 1)
     * @param {number} max - Maximum allowed value (default: 999999)
     * @returns {number|null} - Validated integer or null if invalid
     */
    static validateInteger(value, min = 1, max = 999999) {
        const num = Number(value);
        if (!Number.isInteger(num)) return null;
        if (num < min || num > max) return null;
        return num;
    }

    /**
     * Validate a day of week (0-6)
     * @param {any} value - Day value
     * @returns {number|null} - Valid day (0-6) or null
     */
    static validateDay(value) {
        const day = Number(value);
        return [0, 1, 2, 3, 4, 5, 6].includes(day) ? day : null;
    }

    /**
     * Validate email format
     * @param {string} email - Email to validate
     * @returns {string|null} - Valid email or null
     */
    static validateEmail(email) {
        if (typeof email !== 'string') return null;
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email) ? email : null;
    }

    /**
     * Validate quantity for order items
     * @param {any} qty - Quantity value
     * @param {number} min - Minimum (default: 1)
     * @param {number} max - Maximum (default: 2)
     * @returns {number|null} - Valid quantity or null
     */
    static validateQuantity(qty, min = 1, max = 2) {
        const num = Number(qty);
        if (!Number.isInteger(num) || num < min || num > max) return null;
        return num;
    }

    /**
     * Sanitize a string to prevent XSS
     * Removes HTML tags and limits length
     * @param {string} str - String to sanitize
     * @param {number} maxLength - Maximum length (default: 255)
     * @returns {string} - Sanitized string
     */
    static sanitizeString(str, maxLength = 255) {
        if (typeof str !== 'string') return '';
        return str
            .trim()
            .substring(0, maxLength)
            .replace(/[<>"']/g, ''); // Basic HTML escaping
    }

    /**
     * Validate configuration object from data-* attributes
     * @param {Object} config - Configuration object to validate
     * @returns {Object|null} - Validated config or null
     */
    static validateConfig(config) {
        const validated = {};

        // Validate entrepriseId
        const entrepriseId = this.validateInteger(config.entrepriseId, 1);
        if (!entrepriseId) {
            console.error('Invalid entrepriseId:', config.entrepriseId);
            return null;
        }
        validated.entrepriseId = entrepriseId;

        // Validate weekMenuId
        const weekMenuId = this.validateInteger(config.weekMenuId, 0);
        if (weekMenuId === null) {
            console.error('Invalid weekMenuId:', config.weekMenuId);
            return null;
        }
        validated.weekMenuId = weekMenuId;

        // Validate selectedDay
        const selectedDay = this.validateDay(config.selectedDay);
        if (selectedDay === null) {
            console.error('Invalid selectedDay:', config.selectedDay);
            return null;
        }
        validated.selectedDay = selectedDay;

        // Validate peutPourAutres
        validated.peutPourAutres = config.peutPourAutres === true || config.peutPourAutres === 'true';

        return validated;
    }
}
