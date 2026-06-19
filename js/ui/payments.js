// ============================================================
// PAYMENTS UI Module
// ============================================================

(function() {
    if (window.PaymentsModule) return;
    
    const API = window.autoV_API;
    const Utils = window.autoV_Utils;
    const getServiceDisplay = window.autoV.getServiceDisplay;
    
    window.PaymentsModule = {
        currentPage: 1,
        pageSize: 50,
        
        async load(page = 1) {
            this.currentPage = page;
            console.log('💳 Loading payments...');
            const tbody = document.getElementById('paymentsBody');
            tbody.innerHTML = Utils.renderSpinner();
            
            try {
                const offset = (page - 1) * this.pageSize;
                const { data, error } = await API.getPayments(this.pageSize, offset);
                
                if (error) {
                    tbody.innerHTML = Utils.renderEmpty('❌ ' + error.message);
                    return;
                }
                
                if (!data || data.length === 0) {
                    tbody.innerHTML = Utils.renderEmpty('No payments found');
                    return;
                }
                
                tbody.innerHTML = data.map(p => {
                    const display = getServiceDisplay(p.service_type);
                    const badge = p.status === 'pending' ? 'pending' : 
                                 (p.status === 'completed' || p.status === 'approved' ? 'approved' : 'pending');
                    const user = p.user_id ? p.user_id.substring(0, 12) : 'Unknown';
                    
                    return `<tr>
                        <td>${Utils.formatDate(p.created_at)}</td>
                        <td>${user}</td>
                        <td>${display.icon} ${display.label}</td>
                        <td><strong>${Utils.formatKES(p.amount)}</strong></td>
                        <td><span class="badge badge-${badge}">${p.status}</span></td>
                        <td>
                            <button class="btn btn-secondary btn-sm" onclick="PaymentsModule.viewPayment('${p.id}')">View</button>
                        </td>
                    </tr>`;
                }).join('');
                
            } catch (e) {
                console.error('Payments error:', e);
                tbody.innerHTML = Utils.renderEmpty('Error loading payments');
                Utils.showToast('Error loading payments', 'error');
            }
        },
        
        async viewPayment(id) {
            Utils.showLoading(true);
            try {
                const { data, error } = await API.getPayment(id);
                if (error) throw error;
                
                const display = getServiceDisplay(data.service_type);
                document.getElementById('paymentDetails').innerHTML = `
                    <div style="background:#1e293b;padding:16px;border-radius:12px;">
                        <p><strong>Service:</strong> ${display.icon} ${display.label}</p>
                        <p><strong>Amount:</strong> ${Utils.formatKES(data.amount)}</p>
                        <p><strong>Phone:</strong> ${data.phone || 'N/A'}</p>
                        <p><strong>Status:</strong> ${data.status}</p>
                        <p><strong>Date:</strong> ${Utils.formatDateTime(data.created_at)}</p>
                        ${data.transaction_id ? `<p><strong>Transaction ID:</strong> ${data.transaction_id}</p>` : ''}
                    </div>
                `;
                
                // Set button handlers
                document.getElementById('approvePaymentBtn').onclick = () => this.updateStatus(id, 'approved');
                document.getElementById('rejectPaymentBtn').onclick = () => this.updateStatus(id, 'rejected');
                
                Utils.openModal('paymentModal');
            } catch (e) {
                Utils.showToast('Error loading payment', 'error');
            } finally {
                Utils.showLoading(false);
            }
        },
        
        async updateStatus(id, status) {
            Utils.showConfirm(`Confirm ${status}`, `Are you sure you want to ${status} this payment?`, async () => {
                Utils.showLoading(true);
                try {
                    const { error } = await API.updatePaymentStatus(id, status);
                    if (error) throw error;
                    
                    Utils.showToast(`Payment ${status} successfully`);
                    Utils.closeModal('paymentModal');
                    await this.load(this.currentPage);
                    
                    if (window.OverviewModule && typeof window.OverviewModule.load === 'function') {
                        window.OverviewModule.load();
                    }
                } catch (e) {
                    Utils.showToast('Error updating payment: ' + e.message, 'error');
                } finally {
                    Utils.showLoading(false);
                }
            });
        }
    };
    
    console.log('✅ Payments module loaded');
})();
