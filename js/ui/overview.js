// ============================================================
// OVERVIEW UI Module
// ============================================================

(function() {
    if (window.OverviewModule) return;
    
    const API = window.autoV_API;
    const Utils = window.autoV_Utils;
    const getServiceDisplay = window.autoV.getServiceDisplay;
    
    window.OverviewModule = {
        async load() {
            console.log('📊 Loading overview...');
            const tbody = document.getElementById('recentBody');
            tbody.innerHTML = Utils.renderSpinner();
            
            try {
                const stats = await API.getOverviewStats();
                
                // Update stats
                document.getElementById('totalUsers').textContent = stats.totalUsers;
                document.getElementById('totalRequests').textContent = stats.totalRequests;
                document.getElementById('totalRevenue').innerHTML = Utils.formatKES(stats.totalRevenue);
                document.getElementById('pendingPayments').textContent = stats.pendingPayments;
                
                // Update service counts
                document.getElementById('countInstant').textContent = stats.counts.instant;
                document.getElementById('countValuation').textContent = stats.counts.valuation;
                document.getElementById('countInspection').textContent = stats.counts.inspection;
                document.getElementById('countAssessment').textContent = stats.counts.assessment;
                document.getElementById('countMileage').textContent = stats.counts.mileage;
                document.getElementById('countFleet').textContent = stats.counts.fleet;
                document.getElementById('countVerification').textContent = stats.counts.verification;
                
                // Update recent activity
                this.renderRecentActivity(stats.recentActivity);
                
            } catch (e) {
                console.error('Overview error:', e);
                tbody.innerHTML = Utils.renderEmpty('Error loading activity');
                Utils.showToast('Error loading overview', 'error');
            }
        },
        
        renderRecentActivity(activities) {
            const tbody = document.getElementById('recentBody');
            
            if (!activities || activities.length === 0) {
                tbody.innerHTML = Utils.renderEmpty('No activity yet');
                return;
            }
            
            tbody.innerHTML = activities.slice(0, 10).map(item => {
                const service = item.service_type || 'mileage';
                const display = getServiceDisplay(service);
                const badge = item.status === 'pending' ? 'pending' : 
                             (item.status === 'completed' ? 'completed' : 'approved');
                const user = item.user_id ? item.user_id.substring(0, 12) : 'Unknown';
                const amount = item.amount || item.claim_amount || 0;
                
                return `<tr>
                    <td>${Utils.formatDate(item.created_at)}</td>
                    <td>${user}</td>
                    <td>${display.icon} ${display.label}</td>
                    <td>${Utils.formatKES(amount)}</td>
                    <td><span class="badge badge-${badge}">${item.status || 'pending'}</span></td>
                </tr>`;
            }).join('');
        }
    };
    
    console.log('✅ Overview module loaded');
})();
