// ============================================================
// AUTO-V REPORTS MODULE - Complete
// ============================================================

(function() {
    'use strict';

    // ─── STATE ──────────────────────────────────────────────────────
    let reportsData = [];
    let certificateData = null;
    let currentReport = null;

    // ─── REPORT FUNCTIONS ──────────────────────────────────────────
    async function generateReport(data) {
        try {
            const result = await ApiClient.post('/reports/generate', data);
            currentReport = result;
            ApiClient.showToast('✅ Report generated successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to generate report: ' + error.message, 'error');
            throw error;
        }
    }

    async function getReport(id) {
        try {
            const result = await ApiClient.get(`/reports/${id}`);
            currentReport = result;
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to get report: ' + error.message, 'error');
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
            ApiClient.showToast('❌ Failed to get reports: ' + error.message, 'error');
            throw error;
        }
    }

    function downloadReport(id) {
        window.location.href = `${ApiClient.API_BASE}/reports/download/${id}`;
        ApiClient.showToast('📄 Downloading report...', 'info');
    }

    function viewReport(id) {
        window.open(`${ApiClient.API_BASE}/reports/generate/${id}`, '_blank');
    }

    // ─── CERTIFICATE FUNCTIONS ──────────────────────────────────
    async function createCertificate(data) {
        try {
            const result = await ApiClient.post('/certificates', data);
            certificateData = result;
            ApiClient.showToast('✅ Certificate created successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to create certificate: ' + error.message, 'error');
            throw error;
        }
    }

    async function getCertificate(id) {
        try {
            const result = await ApiClient.get(`/certificates/${id}`);
            certificateData = result;
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to get certificate: ' + error.message, 'error');
            throw error;
        }
    }

    async function getCertificates(params = {}) {
        try {
            const query = new URLSearchParams(params).toString();
            const result = await ApiClient.get(`/certificates?${query}`);
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to get certificates: ' + error.message, 'error');
            throw error;
        }
    }

    function downloadCertificate(id) {
        window.location.href = `${ApiClient.API_BASE}/certificates/download/${id}`;
        ApiClient.showToast('📄 Downloading certificate...', 'info');
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
            ApiClient.showToast('❌ Failed to get last calculation: ' + error.message, 'error');
            throw error;
        }
    }

    // ─── SHARE CERTIFICATE ──────────────────────────────────────────
    function shareCertificate(certId, ref) {
        const verifyUrl = `https://auto-v.vercel.app/verify?ref=${ref || certId}`;
        
        if (navigator.share) {
            navigator.share({
                title: 'AUTO-V Certificate',
                text: `Certificate: ${ref || certId}`,
                url: verifyUrl
            }).catch(() => {});
        } else {
            navigator.clipboard.writeText(`Certificate: ${ref || certId}\nVerify at: ${verifyUrl}`).then(() => {
                ApiClient.showToast('✅ Certificate link copied to clipboard!', 'success');
            }).catch(() => {
                ApiClient.showToast('Share not available', 'error');
            });
        }
    }

    // ─── EXPOSE PUBLIC API ──────────────────────────────────────────
    const Reports = {
        // Reports
        generateReport,
        getReport,
        getReports,
        downloadReport,
        viewReport,

        // Certificates
        createCertificate,
        getCertificate,
        getCertificates,
        downloadCertificate,
        viewCertificate,
        shareCertificate,

        // Helpers
        generateFromLastCalculation,

        // State
        getData: () => reportsData,
        getCertificateData: () => certificateData,
        getCurrent: () => currentReport
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
