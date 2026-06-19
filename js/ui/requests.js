// ============================================================
// ALL REQUESTS UI Module
// ============================================================

(function() {
    if (window.RequestsModule) return;
    
    const API = window.autoV_API;
    const Utils = window.autoV_Utils;
    const getServiceDisplay = window.autoV.getServiceDisplay;
    
    window.RequestsModule = {
        currentPage: 1,
        pageSize: 50,
        
        async load(page = 1) {
            this.currentPage = page;
            console.log('📋 Loading all requests...');
            const tbody = document.getElementById('requestsBody');
            tbody.innerHTML = Utils.renderSpinner();
            
            try {
                const offset = (page - 1) * this.pageSize;
                const { data, error } = await API.getServiceRequests(this.pageSize, offset);
                
                if (error) {
                    tbody.innerHTML = Utils.renderEmpty('❌ ' + error.message);
                    return;
                }
                
                if (!data || data.length === 0) {
                    tbody.innerHTML = Utils.renderEmpty('No service requests found');
                    return;
                }
                
                tbody.innerHTML = data.map(r => {
                    const display = getServiceDisplay(r.service_type);
                    const badge = r.status === 'completed' ? 'completed' : 
                                 (r.status === 'pending' ? 'pending' : 'approved');
                    const user = r.user_id ? r.user_id.substring(0, 12) : 'Unknown';
                    const vehicle = r.registration_number || r.customer_name || 'N/A';
                    
                    return `<tr>
                        <td>${Utils.formatDate(r.created_at)}</td>
                        <td>${user}</td>
                        <td>${display.icon} ${display.label}</td>
                        <td>${vehicle}</td>
                        <td>${Utils.formatKES(r.amount || 0)}</td>
                        <td><span class="badge badge-${badge}">${r.status || 'pending'}</span></td>
                        <td>
                            <button class="btn btn-danger btn-sm" onclick="RequestsModule.deleteRequest('${r.id}')">🗑️</button>
                        </td>
                    </tr>`;
                }).join('');
                
            } catch (e) {
                console.error('Requests error:', e);
                tbody.innerHTML = Utils.renderEmpty('Error loading requests');
                Utils.showToast('Error loading requests', 'error');
            }
        },
        
        async deleteRequest(id) {
            Utils.showConfirm('Delete Request', 'Delete this service request permanently?', async () => {
                Utils.showLoading(true);
                try {
                    const { error } = await API.deleteServiceRequest(id);
                    if (error) throw error;
                    
                    Utils.showToast('✅ Request deleted');
                    await this.load(this.currentPage);
                    
                    // Refresh other modules
                    if (window.OverviewModule && typeof window.OverviewModule.load === 'function') {
                        window.OverviewModule.load();
                    }
                    if (window.ActivitiesModule && typeof window.ActivitiesModule.load === 'function') {
                        window.ActivitiesModule.load();
                    }
                } catch (e) {
                    Utils.showToast('Error deleting request: ' + e.message, 'error');
                } finally {
                    Utils.showLoading(false);
                }
            });
        },
        
        refresh() {
            this.load(this.currentPage);
        }
    };
    
    console.log('✅ Requests module loaded');
})();
