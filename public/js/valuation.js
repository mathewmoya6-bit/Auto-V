// ============================================================
// AUTO-V VALUATION MODULE
// ============================================================

(function() {
    'use strict';

    // ─── STATE ──────────────────────────────────────────────────────
    let valuationData = null;
    let valuationHistory = [];

    // ─── VALUATION FUNCTIONS ──────────────────────────────────────
    async function createValuation(data) {
        try {
            const result = await ApiClient.post('/valuations', data);
            ApiClient.showToast('Valuation created successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to create valuation: ' + error.message, 'error');
            throw error;
        }
    }

    async function getInstantValuation(data) {
        try {
            const result = await ApiClient.post('/valuations/instant', data);
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to get instant valuation: ' + error.message, 'error');
            throw error;
        }
    }

    async function getValuation(id) {
        try {
            const result = await ApiClient.get(`/valuations/${id}`);
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to get valuation: ' + error.message, 'error');
            throw error;
        }
    }

    async function getValuations(params = {}) {
        try {
            const query = new URLSearchParams(params).toString();
            const result = await ApiClient.get(`/valuations?${query}`);
            valuationHistory = result;
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to get valuations: ' + error.message, 'error');
            throw error;
        }
    }

    async function updateValuation(id, data) {
        try {
            const result = await ApiClient.put(`/valuations/${id}`, data);
            ApiClient.showToast('Valuation updated successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to update valuation: ' + error.message, 'error');
            throw error;
        }
    }

    async function deleteValuation(id) {
        try {
            await ApiClient.delete(`/valuations/${id}`);
            ApiClient.showToast('Valuation deleted successfully', 'success');
            return true;
        } catch (error) {
            ApiClient.showToast('Failed to delete valuation: ' + error.message, 'error');
            throw error;
        }
    }

    // ─── VEHICLE FUNCTIONS ──────────────────────────────────────
    async function getVehicleModels() {
        try {
            const result = await ApiClient.get('/vehicles/models');
            return result;
        } catch (error) {
            console.error('Failed to get vehicle models:', error);
            return [];
        }
    }

    async function decodeVIN(vin) {
        try {
            const result = await ApiClient.post('/vehicles/decode-vin', { vin });
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to decode VIN: ' + error.message, 'error');
            throw error;
        }
    }

    // ─── EXTRACT DATA FROM FORM ──────────────────────────────────
    function extractValuationData(form) {
        const formData = new FormData(form);
        return {
            make: formData.get('make'),
            model: formData.get('model'),
            year: parseInt(formData.get('year')),
            engine_capacity: parseInt(formData.get('engineCapacity')) || 0,
            fuel_type: formData.get('fuelType'),
            transmission: formData.get('transmission'),
            body_type: formData.get('bodyType'),
            body_color: formData.get('bodyColor'),
            mileage: parseInt(formData.get('mileage')) || 0,
            condition: formData.get('condition'),
            accident_history: formData.get('accidentHistory'),
            location: formData.get('location'),
            previous_owners: parseInt(formData.get('previousOwners')) || 0,
            usage_type: formData.get('usageType'),
            phone: formData.get('phone')
        };
    }

    // ─── EXPOSE PUBLIC API ──────────────────────────────────────────
    const Valuation = {
        createValuation,
        getInstantValuation,
        getValuation,
        getValuations,
        updateValuation,
        deleteValuation,
        getVehicleModels,
        decodeVIN,
        extractValuationData,
        getHistory: () => valuationHistory
    };

    // ─── EXPOSE GLOBALLY ──────────────────────────────────────────
    if (typeof window !== 'undefined') {
        window.Valuation = Valuation;
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = Valuation;
    }

    console.log('💰 Valuation module initialized');

})();
