// ============================================================
// RATES UI Module
// ============================================================

(function() {
    if (window.RatesModule) return;
    
    const API = window.autoV_API;
    const Utils = window.autoV_Utils;
    
    window.RatesModule = {
        async load() {
            console.log('💰 Loading rates...');
            const container = document.getElementById('ratesContainer');
            container.innerHTML = Utils.renderSpinner();
            
            try {
                const { data, error } = await API.getActiveRates();
                if (error) throw error;
                
                if (!data || data.length === 0) {
                    container.innerHTML = '<p class="empty-state">No rates found</p>';
                    return;
                }
                
                container.innerHTML = data.map(r => `
                    <div class="rate-card">
                        <div class="category">${r.vehicle_category}</div>
                        <div class="rate">${Utils.formatKES(r.rate_per_km)}/km</div>
                        <div class="effective">Eff: ${Utils.formatDate(r.effective_from)}</div>
                        <div style="margin-top:8px;">
                            <button class="btn btn-danger btn-sm" onclick="RatesModule.deleteRate('${r.id}')">Delete</button>
                        </div>
                    </div>
                `).join('');
                
            } catch (e) {
                console.error('Rates error:', e);
                container.innerHTML = '<p class="empty-state">Error loading rates</p>';
                Utils.showToast('Error loading rates', 'error');
            }
        },
        
        async addRate() {
            const category = document.getElementById('rateCategory').value.trim();
            const rate = parseFloat(document.getElementById('rateValue').value);
            const from = document.getElementById('rateEffectiveFrom').value;
            
            if (!category || !rate || !from) {
                Utils.showToast('Please fill all required fields', 'warning');
                return;
            }
            
            Utils.showLoading(true);
            try {
                const { error } = await API.addRate({
                    vehicle_category: category,
                    rate_per_km: rate,
                    effective_from: from,
                    effective_to: document.getElementById('rateEffectiveTo').value || null,
                    is_active: true
                });
                
                if (error) throw error;
                
                Utils.showToast('✅ Rate added successfully');
                
                // Clear form
                document.getElementById('rateCategory').value = '';
                document.getElementById('rateValue').value = '';
                document.getElementById('rateEffectiveFrom').value = '';
                document.getElementById('rateEffectiveTo').value = '';
                
                await this.load();
            } catch (e) {
                Utils.showToast('Error adding rate: ' + e.message, 'error');
            } finally {
                Utils.showLoading(false);
            }
        },
        
        async deleteRate(id) {
            Utils.showConfirm('Delete Rate', 'Are you sure you want to delete this rate?', async () => {
                Utils.showLoading(true);
                try {
                    const { error } = await API.deleteRate(id);
                    if (error) throw error;
                    
                    Utils.showToast('✅ Rate deleted');
                    await this.load();
                } catch (e) {
                    Utils.showToast('Error deleting rate: ' + e.message, 'error');
                } finally {
                    Utils.showLoading(false);
                }
            });
        }
    };
    
    // Setup add rate button
    document.addEventListener('DOMContentLoaded', function() {
        document.getElementById('addRateBtn')?.addEventListener('click', () => {
            window.RatesModule?.addRate();
        });
    });
    
    console.log('✅ Rates module loaded');
})();
