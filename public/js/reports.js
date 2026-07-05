// ============================================================
// AUTO-V REPORTS MODULE
// ============================================================

(function() {
    'use strict';

    // ─── STATE ──────────────────────────────────────────────────────
    let reportsData = [];
    let certificateData = null;

    // ─── REPORT FUNCTIONS ──────────────────────────────────────
    async function generateReport(data) {
        try {
            const result = await ApiClient.post('/reports/generate', data);
            ApiClient.showToast('Report generated successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to generate report: ' + error.message, 'error');
            throw error;
        }
    }

    async function getReport(id) {
        try {
            const result = await ApiClient.get(`/reports/${id}`);
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to get report: ' + error.message, 'error');
            throw error;
        }
    }

    async function getReports(params = {}) {
        try {
            const query = new URLSearchParams(params).toString();
            const result = await ApiClient.get(`/reports?${query}`);
            reportsData = result;
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to get reports: ' + error.message, 'error');
            throw error;
        }
    }

    function downloadReport(id) {
        window.location.href = `${ApiClient.API_BASE}/reports/download/${id}`;
    }

    function viewReport(id) {
        window.open(`${ApiClient.API_BASE}/reports/generate/${id}`, '_blank');
    }

    // ─── CERTIFICATE FUNCTIONS ──────────────────────────────────
    async function createCertificate(data) {
        try {
            const result = await ApiClient.post('/certificates', data);
            ApiClient.showToast('Certificate created successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to create certificate: ' + error.message, 'error');
            throw error;
        }
    }

    async function getCertificate(id) {
        try {
            const result = await ApiClient.get(`/certificates/${id}`);
            certificateData = result;
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to get certificate: ' + error.message, 'error');
            throw error;
        }
    }

    async function getCertificates(params = {}) {
        try {
            const query = new URLSearchParams(params).toString();
            const result = await ApiClient.get(`/certificates?${query}`);
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to get certificates: ' + error.message, 'error');
            throw error;
        }
    }

    function downloadCertificate(id) {
        window.location.href = `${ApiClient.API_BASE}/certificates/download/${id}`;
    }

    function viewCertificate(id) {
        window.open(`${ApiClient.API_BASE}/certificates/view/${id}`, '_blank');
    }

    // ─── GENERATE FROM LAST CALCULATION ──────────────────────────
    async function generateFromLastCalculation(type) {
        try {
            const result = await ApiClient.get(`/calculations/last?type=${type}`);
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to get last calculation: ' + error.message, 'error');
            throw error;
        }
    }

    // ─── EXPOSE PUBLIC API ──────────────────────────────────────────
    const Reports = {
        generateReport,
        getReport,
        getReports,
        downloadReport,
        viewReport,
        createCertificate,
        getCertificate,
        getCertificates,
        downloadCertificate,
        viewCertificate,
        generateFromLastCalculation,
        getData: () => reportsData,
        getCertificateData: () => certificateData
    };

    // ─── EXPOSE GLOBALLY ──────────────────────────────────────────
    if (typeof window !== 'undefined') {
        window.Reports = Reports;
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = Reports;
    }

    console.log('📄 Reports module initialized');

})();
