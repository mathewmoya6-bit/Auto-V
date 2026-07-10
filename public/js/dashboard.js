// ============================================================
// AUTO-V DASHBOARD MODULE
// ============================================================

(function() {
    'use strict';

    // ─── CONFIG ──────────────────────────────────────────────────────
    const SERVICES = [
        { id: 'instant', icon: '💡', name: 'Instant Value Check', desc: 'Quick AI market estimate', page: 'instant-value.html' },
        { id: 'valuation', icon: '💰', name: 'Vehicle Valuation', desc: 'Certified valuation report', page: 'valuation.html' },
        { id: 'inspection', icon: '🔍', name: 'Vehicle Inspection', desc: 'Comprehensive inspection report', page: 'inspection.html' },
        { id: 'assessment', icon: '⚠️', name: 'Vehicle Assessment', desc: 'Accident and damage assessment', page: 'assessment.html' },
        { id: 'mileage', icon: '📏', name: 'Mileage Rate', desc: 'Cost per kilometre analysis', page: 'mileage.html' },
        { id: 'fleet', icon: '🚛', name: 'Fleet Services', desc: 'Full fleet management', page: 'fleet.html' }
    ];

    // ─── STATE ──────────────────────────────────────────────────────
    let dashboardData = {
        vehicles: [],
        reports: [],
        certificates: [],
        stats: {
            totalVehicles: 0,
            totalReports: 0,
            totalCertificates: 0,
            totalValue: 0
        }
    };

    // ─── LOAD FUNCTIONS ──────────────────────────────────────────
    async function loadDashboard() {
        try {
            const [vehicles, reports, certificates, stats] = await Promise.all([
                ApiClient.get('/vehicles'),
                ApiClient.get('/service-requests'),
                ApiClient.get('/certificates'),
                getStats()
            ]);

            dashboardData.vehicles = vehicles || [];
            dashboardData.reports = reports || [];
            dashboardData.certificates = certificates || [];
            dashboardData.stats = stats;

            renderDashboard();
            return dashboardData;
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            ApiClient.showToast('Failed to load dashboard data', 'error');
            throw error;
        }
    }

    async function getStats() {
        try {
            const [vehicles, reports, certificates, valuations] = await Promise.all([
                ApiClient.get('/vehicles/count'),
                ApiClient.get('/service-requests/count'),
                ApiClient.get('/certificates/count'),
                ApiClient.get('/valuations/total')
            ]);

            return {
                totalVehicles: vehicles.count || 0,
                totalReports: reports.count || 0,
                totalCertificates: certificates.count || 0,
                totalValue: valuations.total || 0
            };
        } catch (error) {
            console.warn('Failed to load stats:', error);
            return {
                totalVehicles: 0,
                totalReports: 0,
                totalCertificates: 0,
                totalValue: 0
            };
        }
    }

    // ─── RENDER FUNCTIONS ──────────────────────────────────────────
    function renderDashboard() {
        renderStats();
        renderServices();
        renderVehicles();
        renderReports();
        renderCertificates();
    }

    function renderStats() {
        const stats = dashboardData.stats;
        document.getElementById('sumVehicles').textContent = stats.totalVehicles;
        document.getElementById('sumReports').textContent = stats.totalReports;
        document.getElementById('sumCertificates').textContent = stats.totalCertificates;
        document.getElementById('sumValue').textContent = `KES ${formatNumber(stats.totalValue)}`;
    }

    function renderServices() {
        const container = document.getElementById('serviceGrid');
        if (!container) return;

        container.innerHTML = SERVICES.map(s => `
            <div class="service-card">
                <span class="service-icon">${s.icon}</span>
                <h3>${s.name}</h3>
                <p>${s.desc}</p>
                <div class="service-actions">
                    <a href="${s.page}" class="btn">Start Service</a>
                    <a href="#" class="btn btn-outline" onclick="event.preventDefault(); showServiceInfo('${s.id}')">Learn More</a>
                </div>
            </div>
        `).join('');
    }

    function renderVehicles() {
        const container = document.getElementById('vehicleList');
        if (!container) return;

        const vehicles = dashboardData.vehicles.slice(0, 5);
        if (!vehicles.length) {
            container.innerHTML = `<div class="empty-state">🚗 You haven't registered any vehicles yet. <a href="customer-portal.html">Add your first vehicle</a></div>`;
            return;
        }

        container.innerHTML = vehicles.map(v => `
            <div class="list-item">
                <div class="info">
                    <h4>${v.make || 'Unknown'} ${v.model || ''}</h4>
                    <p>${v.license_plate || v.registration_number || 'No plate'} · ${v.year || 'N/A'}</p>
                </div>
                <div class="actions">
                    <button class="btn-sm" onclick="window.Dashboard.viewVehicleHistory('${v.id}')">View History</button>
                    <button class="btn-sm" onclick="window.location.href='customer-portal.html?service=valuation&vehicle=${v.id}'">Valuation</button>
                </div>
            </div>
        `).join('');
    }

    function renderReports() {
        const container = document.getElementById('recentReports');
        if (!container) return;

        const reports = dashboardData.reports.slice(0, 5);
        if (!reports.length) {
            container.innerHTML = `<div class="empty-state">No reports generated yet.</div>`;
            return;
        }

        container.innerHTML = reports.map(r => `
            <div class="list-item">
                <div class="info">
                    <h4>${r.vehicle_make || 'N/A'} ${r.vehicle_model || ''} · ${getServiceName(r.service_type)}</h4>
                    <p>${formatDate(r.created_at)}</p>
                </div>
                <div class="actions">
                    <span class="status-badge ${r.status || 'pending'}">${r.status || 'Pending'}</span>
                    <button class="btn-sm" onclick="window.Dashboard.viewReport('${r.id}')">View</button>
                    ${r.status === 'completed' ? `<button class="btn-sm" onclick="window.Dashboard.downloadReport('${r.id}')">📥 PDF</button>` : ''}
                </div>
            </div>
        `).join('');
    }

    function renderCertificates() {
        const container = document.getElementById('certificateList');
        if (!container) return;

        const certificates = dashboardData.certificates.slice(0, 5);
        if (!certificates.length) {
            container.innerHTML = `<div class="empty-state">No certificates issued yet.</div>`;
            return;
        }

        container.innerHTML = certificates.map(c => `
            <div class="list-item">
                <div class="info">
                    <h4>${c.certificate_number || c.id}</h4>
                    <p>${c.vehicle_make || 'N/A'} ${c.vehicle_model || ''} · ${c.status === 'active' ? '✅ Verified' : '⏳ Pending'}</p>
                </div>
                <div class="actions">
                    <button class="btn-sm" onclick="window.Dashboard.downloadCertificate('${c.id}')">📥 Download</button>
                    <button class="btn-sm" onclick="window.Dashboard.viewCertificate('${c.id}')">🖨 Print</button>
                </div>
            </div>
        `).join('');
    }

    // ─── ACTION HANDLERS ──────────────────────────────────────────
    function viewReport(requestId) {
        window.open(`${ApiClient.API_BASE}/reports/generate/${requestId}`, '_blank');
    }

    function downloadReport(requestId) {
        window.location.href = `${ApiClient.API_BASE}/reports/download/${requestId}`;
    }

    function viewCertificate(certId) {
        window.open(`${ApiClient.API_BASE}/certificates/view/${certId}`, '_blank');
    }

    function downloadCertificate(certId) {
        window.location.href = `${ApiClient.API_BASE}/certificates/download/${certId}`;
    }

    function viewVehicleHistory(vehicleId) {
        window.location.href = `vehicle-history.html?id=${vehicleId}`;
    }

    function showServiceInfo(serviceId) {
        const service = SERVICES.find(s => s.id === serviceId);
        if (service) {
            ApiClient.showToast(`${service.name}: ${service.desc}. Click "Start Service" to begin.`, 'info');
        }
    }

    // ─── EXPOSE PUBLIC API ──────────────────────────────────────────
    const Dashboard = {
        loadDashboard,
        getData: () => dashboardData,
        viewReport,
        downloadReport,
        viewCertificate,
        downloadCertificate,
        viewVehicleHistory,
        showServiceInfo,
        renderDashboard
    };

    // ─── EXPOSE GLOBALLY ──────────────────────────────────────────
    if (typeof window !== 'undefined') {
        window.Dashboard = Dashboard;
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = Dashboard;
    }

    console.log('📊 Dashboard module initialized');

})();
