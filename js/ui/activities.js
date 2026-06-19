// ============================================================
// ACTIVITIES UI Module
// ============================================================

(function() {
    if (window.ActivitiesModule) return;
    
    const API = window.autoV_API;
    const Utils = window.autoV_Utils;
    const getServiceDisplay = window.autoV.getServiceDisplay;
    
    window.ActivitiesModule = {
        async load() {
            console.log('📋 Loading activities...');
            const tbody = document.getElementById('activitiesBody');
            tbody.innerHTML = Utils.renderSpinner();
            
            try {
                // Fetch all data sources
                const [requests, claims, payments] = await Promise.all([
                    API.getServiceRequests(100, 0),
                    API.getMileageClaims(100, 0),
                    API.getPayments(100, 0)
                ]);
                
                // Combine and format
                const all = [];
                
                (requests.data || []).forEach(r => {
                    const display = getServiceDisplay(r.service_type);
                    all.push({
                        date: r.created_at,
                        user: r.user_id,
                        service: display.icon + ' ' + display.label,
                        details: r.customer_name || r.registration_number || 'N/A',
                        amount: r.amount || 0,
                        status: r.status || 'pending',
                        type: 'request'
                    });
                });
                
                (claims.data || []).forEach(c => {
                    all.push({
                        date: c.created_at,
                        user: c.user_id,
                        service: '📏 Mileage Claim',
                        details: (c.start_location || '') + ' → ' + (c.end_location || ''),
                        amount: c.claim_amount || 0,
                        status: c.status || 'pending',
                        type: 'claim'
                    });
                });
                
                (payments.data || []).forEach(p => {
                    const display = getServiceDisplay(p.service_type);
                    all.push({
                        date: p.created_at,
                        user: p.user_id,
                        service: '💳 ' + display.label + ' Payment',
                        details: p.reference || p.service_type || 'Payment',
                        amount: p.amount || 0,
                        status: p.status || 'pending',
                        type: 'payment'
                    });
                });
                
                // Sort by date
                all.sort((a, b) => new Date(b.date) - new Date(a.date));
                
                if (all.length === 0) {
                    tbody.innerHTML = Utils.renderEmpty('No activities found');
                    return;
                }
                
                tbody.innerHTML = all.slice(0, 50).map(item => {
                    const badge = item.status === 'pending' ? 'pending' : 
                                 (item.status === 'completed' || item.status === 'approved' ? 'approved' : 'pending');
                    const user = item.user ? item.user.substring(0, 12) : 'Unknown';
                    
                    return `<tr>
                        <td>${Utils.formatDate(item.date)}</td>
                        <td>${user}</td>
                        <td>${item.service}</td>
                        <td>${item.details}</td>
                        <td>${Utils.formatKES(item.amount)}</td>
                        <td><span class="badge badge-${badge}">${item.status}</span></td>
                    </tr>`;
                }).join('');
                
            } catch (e) {
                console.error('Activities error:', e);
                tbody.innerHTML = Utils.renderEmpty('Error loading activities');
                Utils.showToast('Error loading activities', 'error');
            }
        }
    };
    
    console.log('✅ Activities module loaded');
})();
