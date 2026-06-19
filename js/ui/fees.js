// ============================================================
// SERVICE FEES UI Module
// ============================================================

(function() {
    if (window.FeesModule) return;
    
    const API = window.autoV_API;
    const Utils = window.autoV_Utils;
    const purposeOptions = window.autoV.purposeOptions;
    const serviceMap = window.autoV.serviceMap;
    
    window.FeesModule = {
        async load() {
            console.log('🔧 Loading fees...');
            const container = document.getElementById('feesContainer');
            container.innerHTML = Utils.renderSpinner();
            
            try {
                const { data, error } = await API.getFees();
                if (error) throw error;
                
                // Create fee map
                const feeMap = {};
                (data || []).forEach(row => {
                    feeMap[row.setting_key] = row.setting_value;
                });
                
                let html = '';
                
                // ─── Flat Fees ──────────────────────────────────────
                const flatFees = [
                    { key: 'instant_fee', label: '💡 Instant Value Check', default: 500 },
                    { key: 'mileage_fee', label: '📏 Mileage Rate Report', default: 1500 },
                    { key: 'fleet_fee', label: '🚛 Fleet Services', default: 4000 },
                    { key: 'verification_fee', label: '✅ Report Verification', default: 1000 }
                ];
                
                flatFees.forEach(f => {
                    const value = feeMap[f.key] || f.default;
                    html += `
                        <div class="fee-item">
                            <div class="fee-label">${f.label}</div>
                            <div class="fee-input">
                                <input type="number" id="fee_${f.key}" step="100" value="${value}">
                            </div>
                            <div class="fee-save">
                                <button class="btn btn-success btn-sm" onclick="FeesModule.saveFee('${f.key}')">💾 Save</button>
                            </div>
                        </div>
                    `;
                });
                
                // ─── Purpose-Specific Fees ──────────────────────────
                ['valuation', 'inspection', 'assessment'].forEach(service => {
                    const purposes = purposeOptions[service] || [];
                    if (purposes.length === 0) return;
                    
                    html += `
                        <div style="margin-top:20px;">
                            <h3 style="color:#eab308;font-size:14px;margin-bottom:10px;">
                                ${serviceMap[service].icon} ${serviceMap[service].label}
                            </h3>
                    `;
                    
                    purposes.forEach(purpose => {
                        const key = service + '_' + purpose.toLowerCase().replace(/[^a-z0-9]/g, '_') + '_fee';
                        const value = feeMap[key] || 0;
                        html += `
                            <div class="fee-item">
                                <div class="fee-label">${purpose}</div>
                                <div class="fee-input">
                                    <input type="number" id="fee_${key}" step="100" value="${value}">
                                </div>
                                <div class="fee-save">
                                    <button class="btn btn-success btn-sm" onclick="FeesModule.saveFee('${key}')">💾 Save</button>
                                </div>
                            </div>
                        `;
                    });
                    
                    html += `</div>`;
                });
                
                container.innerHTML = html;
                
            } catch (e) {
                console.error('Fees error:', e);
                container.innerHTML = '<p class="empty-state">Error loading fees</p>';
                Utils.showToast('Error loading fees', 'error');
            }
        },
        
        async saveFee(key) {
            const input = document.getElementById('fee_' + key);
            if (!input) return;
            
            const value = parseFloat(input.value);
            if (isNaN(value) || value < 0) {
                Utils.showToast('Please enter a valid amount', 'warning');
                return;
            }
            
            Utils.showLoading(true);
            try {
                const { error } = await API.saveFee(key, value);
                if (error) throw error;
                
                // Update input to show saved value
                input.value = value;
                
                const label = key.replace(/_fee$/, '').replace(/_/g, ' ').toUpperCase();
                Utils.showToast(`✅ ${label} updated to ${Utils.formatKES(value)}`, 'success');
            } catch (e) {
                Utils.showToast('Error saving fee: ' + e.message, 'error');
            } finally {
                Utils.showLoading(false);
            }
        }
    };
    
    console.log('✅ Fees module loaded');
})();
