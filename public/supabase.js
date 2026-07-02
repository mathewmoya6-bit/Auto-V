// ============================================
// AUTO-V SUPABASE CONFIGURATION
// Single Source of Truth - Real-time Sync
// ============================================

// ✅ GUARD: Prevent double initialization
if (window.autoV && window.autoV._initialized) {
    console.log('✅ AUTO-V Supabase already initialized, skipping...');
} else {
    (function() {
        'use strict';

        // ─── Configuration ──────────────────────────────────────────────
        const SUPABASE_URL = "https://tsvejnzxrxrrecgquxbq.supabase.co";
        const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ";

        // ─── Create Supabase client ──────────────────────────────────────
        if (typeof window.supabase === 'undefined' || !window.supabase.createClient) {
            console.error('❌ Supabase CDN not loaded. Please check the script tag.');
            return;
        }

        const supabase = window.supabase.createClient(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            {
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'apikey': SUPABASE_ANON_KEY
                }
            }
        );
        console.log('✅ Supabase client created with proper headers');

        // ─── Shared State ──────────────────────────────────────────────
        const state = {
            fees: {
                instant: 500,
                valuation: 2500,
                inspection: 3500,
                assessment: 3000,
                mileage: 1500,
                fleet: 4000,
                verification: 1000,
                professional: 5000
            },
            stats: {
                users: 0,
                requests: 0,
                revenue: 0,
                pending: 0,
                instant: 0,
                vehicles: 0,
                inspections: 0
            },
            lastUpdated: null,
            listeners: [],
            subscriptions: []
        };

        // ─── Data Fetching Functions ────────────────────────────────────
        async function fetchFees() {
            try {
                // Try to fetch from system_settings table
                const { data, error } = await supabase
                    .from('system_settings')
                    .select('setting_key, setting_value');
                
                if (!error && data) {
                    const feeMap = {
                        'instant_fee': 'instant',
                        'valuation_fee': 'valuation',
                        'inspection_fee': 'inspection',
                        'assessment_fee': 'assessment',
                        'mileage_fee': 'mileage',
                        'fleet_fee': 'fleet',
                        'verification_fee': 'verification',
                        'professional_fee': 'professional'
                    };
                    
                    data.forEach(row => {
                        const key = feeMap[row.setting_key];
                        if (key) {
                            state.fees[key] = parseInt(row.setting_value) || state.fees[key];
                        }
                    });
                }
                
                // Also try system_fees table
                const { data: feeData, error: feeError } = await supabase
                    .from('system_fees')
                    .select('service_type, fee');
                
                if (!feeError && feeData) {
                    const feeMap = {
                        'instant-value-check': 'instant',
                        'mileage-rate': 'mileage',
                        'valuation': 'valuation',
                        'inspection': 'inspection',
                        'assessment': 'assessment',
                        'fleet': 'fleet'
                    };
                    
                    feeData.forEach(row => {
                        const key = feeMap[row.service_type];
                        if (key) {
                            state.fees[key] = row.fee || state.fees[key];
                        }
                    });
                }
                
                return state.fees;
            } catch (err) {
                console.warn('⚠️ Could not fetch fees:', err.message);
                return state.fees;
            }
        }

        async function fetchStats() {
            try {
                // Try to get counts from various tables
                let users = 0, requests = 0, instant = 0, vehicles = 0, inspections = 0;
                
                try {
                    const { count: userCount } = await supabase
                        .from('user_profiles')
                        .select('*', { count: 'exact', head: true });
                    users = userCount || 0;
                } catch (e) { /* table may not exist */ }
                
                try {
                    const { count: requestCount } = await supabase
                        .from('service_requests')
                        .select('*', { count: 'exact', head: true });
                    requests = requestCount || 0;
                } catch (e) { /* table may not exist */ }
                
                try {
                    const { count: instantCount } = await supabase
                        .from('service_requests')
                        .select('*', { count: 'exact', head: true })
                        .eq('service_type', 'instant');
                    instant = instantCount || 0;
                } catch (e) { /* table may not exist */ }
                
                try {
                    const { count: vehicleCount } = await supabase
                        .from('service_requests')
                        .select('*', { count: 'exact', head: true })
                        .eq('service_type', 'valuation');
                    vehicles = vehicleCount || 0;
                } catch (e) { /* table may not exist */ }
                
                try {
                    const { count: inspectionCount } = await supabase
                        .from('service_requests')
                        .select('*', { count: 'exact', head: true })
                        .eq('service_type', 'inspection');
                    inspections = inspectionCount || 0;
                } catch (e) { /* table may not exist */ }

                // Try to get revenue from payments
                let revenue = 0, pending = 0;
                try {
                    const { data: payments } = await supabase
                        .from('payments')
                        .select('amount, status');
                    
                    if (payments) {
                        revenue = payments.reduce((s, p) => s + (p.amount || 0), 0) || 0;
                        pending = payments.filter(p => p.status === 'pending').length || 0;
                    }
                } catch (e) { /* table may not exist */ }

                state.stats = {
                    users: users || 0,
                    requests: requests || 0,
                    revenue: revenue || 0,
                    pending: pending || 0,
                    instant: instant || 0,
                    vehicles: vehicles || 0,
                    inspections: inspections || 0
                };
                state.lastUpdated = new Date();
                
                return state.stats;
            } catch (err) {
                console.warn('⚠️ Could not fetch stats:', err.message);
                return state.stats;
            }
        }

        async function fetchAllData() {
            await Promise.all([fetchFees(), fetchStats()]);
            notifyListeners();
            return { fees: state.fees, stats: state.stats };
        }

        // ─── Real-time Subscriptions ────────────────────────────────────
        function subscribeToChanges(callback) {
            const tables = ['system_settings', 'system_fees', 'service_requests', 'payments', 'user_profiles'];
            
            tables.forEach(table => {
                try {
                    const channel = supabase
                        .channel(`public:${table}`)
                        .on('postgres_changes', 
                            { event: '*', schema: 'public', table: table },
                            () => {
                                console.log(`🔄 ${table} changed, refreshing...`);
                                fetchAllData().then(() => {
                                    if (callback) callback();
                                });
                            }
                        )
                        .subscribe();
                    
                    state.subscriptions.push(channel);
                } catch (e) {
                    console.warn(`⚠️ Could not subscribe to ${table}:`, e.message);
                }
            });
        }

        // ─── Listener System ────────────────────────────────────────────
        function addListener(callback) {
            if (typeof callback === 'function') {
                state.listeners.push(callback);
            }
        }

        function removeListener(callback) {
            state.listeners = state.listeners.filter(cb => cb !== callback);
        }

        function notifyListeners() {
            state.listeners.forEach(cb => {
                try {
                    cb({ fees: state.fees, stats: state.stats });
                } catch (err) {
                    console.warn('Listener error:', err);
                }
            });
        }

        // ─── Toast System ──────────────────────────────────────────────
        function showToast(message, type = 'success') {
            const existing = document.querySelector('.toast');
            if (existing) existing.remove();
            
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            toast.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                padding: 12px 24px;
                background: ${type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : type === 'warning' ? '#eab308' : '#3b82f6'};
                color: ${type === 'success' || type === 'warning' ? '#000' : '#fff'};
                border-radius: 8px;
                z-index: 9999;
                font-weight: 500;
                animation: slideIn 0.3s ease;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                max-width: 400px;
                font-family: 'Inter', system-ui, sans-serif;
            `;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

        // ─── Live Indicator ─────────────────────────────────────────────
        function getLiveIndicator() {
            return `
                <span class="live-indicator">
                    <span class="dot"></span> Live
                </span>
            `;
        }

        // ─── Build the complete object ─────────────────────────────────
        const autoVInstance = {
            // Core
            supabase: supabase,
            SUPABASE_URL: SUPABASE_URL,
            SUPABASE_ANON_KEY: SUPABASE_ANON_KEY,
            state: state,
            _initialized: true,
            
            // ─── Data Functions ──────────────────────────────────────────
            fetchFees: fetchFees,
            fetchStats: fetchStats,
            fetchAllData: fetchAllData,
            refresh: fetchAllData,
            
            // ─── Real-time Sync ──────────────────────────────────────────
            subscribeToChanges: subscribeToChanges,
            addListener: addListener,
            removeListener: removeListener,
            getLiveIndicator: getLiveIndicator,
            
            // ─── Toast ────────────────────────────────────────────────────
            showToast: showToast,
            
            // ─── Formatting ──────────────────────────────────────────────
            formatKES(amount) {
                if (amount === undefined || amount === null) return 'KES 0';
                return 'KES ' + Number(amount).toLocaleString('en-KE');
            },
            
            formatDate(date, format = 'short') {
                if (!date) return '—';
                const d = new Date(date);
                if (format === 'short') return d.toLocaleDateString('en-KE', { day: '2-digit', month: 'short', year: 'numeric' });
                if (format === 'long') return d.toLocaleDateString('en-KE', { day: 'numeric', month: 'long', year: 'numeric' });
                if (format === 'datetime') return d.toLocaleString('en-KE', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
                if (format === 'time') return d.toLocaleTimeString('en-KE', { hour: '2-digit', minute: '2-digit' });
                return d.toISOString().split('T')[0];
            },
            
            formatNumber(num) {
                if (num === undefined || num === null) return '0';
                return Number(num).toLocaleString('en-KE');
            },
            
            getServiceName(type) {
                const map = {
                    'instant': '💡 Instant Value Check',
                    'instant-value-check': '💡 Instant Value Check',
                    'valuation': '💰 Vehicle Valuation',
                    'inspection': '🔍 Vehicle Inspection',
                    'assessment': '⚠️ Vehicle Assessment',
                    'mileage': '📏 Mileage Rate Report',
                    'mileage-rate': '📏 Mileage Rate Report',
                    'fleet': '🚛 Fleet Services',
                    'verification': '✅ Report Verification',
                    'report-verification': '✅ Report Verification'
                };
                return map[type] || type || 'N/A';
            },
            
            getStatusBadge(status) {
                const map = {
                    'completed': 'badge-completed',
                    'paid': 'badge-paid',
                    'pending': 'badge-pending',
                    'processing': 'badge-processing',
                    'failed': 'badge-failed',
                    'cancelled': 'badge-cancelled',
                    'active': 'badge-active',
                    'inactive': 'badge-inactive',
                    'refunded': 'badge-cancelled'
                };
                return map[status] || 'badge-pending';
            },
            
            // ─── AUTHENTICATION ──────────────────────────────────────────
            async getCurrentUser() {
                try {
                    const { data: { user }, error } = await supabase.auth.getUser();
                    if (error || !user) return null;
                    return user;
                } catch (e) {
                    return null;
                }
            },
            
            async requireAuth() {
                const user = await this.getCurrentUser();
                if (!user) {
                    window.location.href = "login.html";
                    return null;
                }
                return user;
            },
            
            async logout() {
                await supabase.auth.signOut();
                localStorage.clear();
                sessionStorage.clear();
                window.location.href = "login.html";
            },
            
            // ─── USER PROFILE ─────────────────────────────────────────
            async upsertUserProfile(userId, email, role) {
                try {
                    const { data, error } = await supabase
                        .from('user_profiles')
                        .upsert({
                            user_id: userId,
                            full_name: email?.split('@')[0] || 'User',
                            email: email,
                            role: role || 'individual',
                            updated_at: new Date().toISOString()
                        }, { onConflict: 'user_id' })
                        .select();
                    
                    if (error) {
                        console.warn('Error upserting user profile:', error.message);
                        return { data: null, error: error };
                    }
                    return { data, error: null };
                } catch (err) {
                    console.warn('Error in upsertUserProfile:', err);
                    return { data: null, error: err };
                }
            },
            
            async getUserRole(userId) {
                try {
                    const { data, error } = await supabase
                        .from('user_profiles')
                        .select('role')
                        .eq('user_id', userId)
                        .single();
                    if (error || !data) return 'individual';
                    return data.role;
                } catch (err) {
                    console.warn('Error getting role:', err);
                    return 'individual';
                }
            },

            // ─── Valuation ──────────────────────────────────────────────
            calculateValuation(vehicleData) {
                const {
                    make = 'Toyota',
                    year = 2020,
                    odometer = 50000,
                    condition = 'Good',
                    accident = 'None'
                } = vehicleData;
                
                const baseValues = {
                    toyota: 2800000,
                    mercedes: 5000000,
                    bmw: 4500000,
                    honda: 2500000,
                    nissan: 2300000,
                    mazda: 2200000,
                    subaru: 2600000,
                    volkswagen: 2400000,
                    hyundai: 2000000,
                    ford: 2100000
                };
                
                const defaultBase = 2000000;
                const baseValue = baseValues[make.toLowerCase()] || defaultBase;
                
                const currentYear = new Date().getFullYear();
                const age = currentYear - year;
                const ageFactor = Math.max(0.35, 1 - (age * 0.08));
                const mileageFactor = Math.max(0.45, 1 - (odometer / 300000));
                
                const conditionFactors = {
                    'Excellent': 1.15,
                    'Good': 1.0,
                    'Fair': 0.85,
                    'Poor': 0.7
                };
                const conditionFactor = conditionFactors[condition] || 1.0;
                
                const accidentFactors = {
                    'None': 1.0,
                    'Minor': 0.85,
                    'Moderate': 0.65,
                    'Major': 0.4
                };
                const accidentFactor = accidentFactors[accident] || 1.0;
                
                let marketValue = Math.round(baseValue * ageFactor * mileageFactor * conditionFactor * accidentFactor);
                marketValue = Math.max(150000, Math.min(marketValue, baseValue * 1.2));
                
                const insuranceValue = Math.round(marketValue * 1.1);
                const tradeInValue = Math.round(marketValue * 0.8);
                const forcedSaleValue = Math.round(marketValue * 0.7);
                const certificateNumber = `AUTO-${Date.now()}-${Math.random().toString(36).substring(2, 10).toUpperCase()}`;
                
                return {
                    market_value: marketValue,
                    insurance_value: insuranceValue,
                    trade_in_value: tradeInValue,
                    forced_sale_value: forcedSaleValue,
                    certificate_number: certificateNumber,
                    valuation_date: new Date().toISOString(),
                    factors_used: {
                        base_value: baseValue,
                        age_factor: ageFactor,
                        mileage_factor: mileageFactor,
                        condition_factor: conditionFactor,
                        accident_factor: accidentFactor
                    }
                };
            },
            
            // ─── Service Requests ──────────────────────────────────────
            async saveServiceRequest(requestData) {
                const user = await this.getCurrentUser();
                if (!user) return { error: 'Not authenticated' };
                
                try {
                    const { data, error } = await supabase
                        .from('service_requests')
                        .insert([{
                            user_id: user.id,
                            ...requestData,
                            payment_status: 'paid',
                            status: 'completed',
                            created_at: new Date().toISOString()
                        }])
                        .select();
                    
                    return { data, error };
                } catch (e) {
                    return { data: null, error: e };
                }
            },
            
            async getUserServiceHistory() {
                const user = await this.getCurrentUser();
                if (!user) return [];
                try {
                    const { data, error } = await supabase
                        .from('service_requests')
                        .select('*')
                        .eq('user_id', user.id)
                        .order('created_at', { ascending: false });
                    if (error) return [];
                    return data || [];
                } catch (e) {
                    return [];
                }
            },
            
            // ─── Report Generation ──────────────────────────────────────
            generateReportHTML(type, data) {
                if (type === 'valuation') {
                    return `
                        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                            <div style="text-align: center; border-bottom: 2px solid #eab308; padding-bottom: 20px;">
                                <h1 style="color: #eab308;">AUTO-V Valuation Report</h1>
                                <p>Certificate: ${data.certificate_number || 'N/A'}</p>
                                <p>Date: ${this.formatDate(new Date(), 'long')}</p>
                            </div>
                            <div style="margin: 20px 0;">
                                <h3>Vehicle Details</h3>
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Make:</strong></td><td>${data.make || 'N/A'}</td></tr>
                                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Model:</strong></td><td>${data.model || 'N/A'}</td></tr>
                                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Year:</strong></td><td>${data.year || 'N/A'}</td></tr>
                                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Registration:</strong></td><td>${data.registration_number || 'N/A'}</td></tr>
                                </table>
                            </div>
                            <div style="margin: 20px 0;">
                                <h3>Valuation Results</h3>
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr><td style="padding: 8px; background: #f5f5f5;"><strong>Market Value:</strong></td><td style="padding: 8px; color: #22c55e; font-size: 24px;">${this.formatKES(data.market_value)}</td></tr>
                                    <tr><td style="padding: 8px;"><strong>Insurance Value:</strong></td><td>${this.formatKES(data.insurance_value)}</td></tr>
                                    <tr><td style="padding: 8px;"><strong>Trade-In Value:</strong></td><td>${this.formatKES(data.trade_in_value)}</td></tr>
                                    <tr><td style="padding: 8px;"><strong>Forced Sale Value:</strong></td><td>${this.formatKES(data.forced_sale_value)}</td></tr>
                                </table>
                            </div>
                            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
                                <p>This report is generated by AUTO-V Vehicle Intelligence Platform</p>
                                <p>Valid for 90 days from issue date</p>
                            </div>
                        </div>
                    `;
                }
                return '<p>Report not available</p>';
            },
            
            async downloadReport(type, data) {
                const html = this.generateReportHTML(type, data);
                const blob = new Blob([html], { type: 'text/html' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `AUTO-V_${type}_${data.certificate_number || Date.now()}.html`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            },
            
            // ─── Mileage ──────────────────────────────────────────────────
            async getMileageRate(vehicleCategory) {
                if (!vehicleCategory) return 25;
                try {
                    const { data, error } = await supabase
                        .from('mileage_rates')
                        .select('rate_per_km')
                        .eq('vehicle_category', vehicleCategory)
                        .eq('is_active', true)
                        .single();
                    if (error || !data) return 25;
                    return data.rate_per_km;
                } catch (e) {
                    return 25;
                }
            },
            
            async getAllMileageRates() {
                try {
                    const { data, error } = await supabase
                        .from('mileage_rates')
                        .select('*')
                        .eq('is_active', true)
                        .order('rate_per_km');
                    if (error) return [];
                    return data || [];
                } catch (e) {
                    return [];
                }
            },
            
            async submitMileageClaim(claimData) {
                const user = await this.getCurrentUser();
                if (!user) return { error: 'Not authenticated' };
                
                try {
                    const { data, error } = await supabase
                        .from('mileage_claims')
                        .insert([{
                            user_id: user.id,
                            employee_name: user.email?.split('@')[0] || 'Employee',
                            ...claimData,
                            status: 'pending'
                        }])
                        .select();
                    return { data, error };
                } catch (e) {
                    return { data: null, error: e };
                }
            },
            
            async getUserMileageClaims() {
                const user = await this.getCurrentUser();
                if (!user) return [];
                try {
                    const { data, error } = await supabase
                        .from('mileage_claims')
                        .select('*')
                        .eq('user_id', user.id)
                        .order('trip_date', { ascending: false });
                    if (error) return [];
                    return data || [];
                } catch (e) {
                    return [];
                }
            },
            
            async cancelMileageClaim(claimId) {
                try {
                    const { error } = await supabase
                        .from('mileage_claims')
                        .delete()
                        .eq('id', claimId);
                    return { success: !error, error };
                } catch (e) {
                    return { success: false, error: e };
                }
            },
            
            // ─── Fleet ───────────────────────────────────────────────────
            async getFleetVehicles(organizationId = null) {
                try {
                    let query = supabase.from('fleet_vehicles').select('*');
                    if (organizationId) query = query.eq('organization_id', organizationId);
                    const { data, error } = await query;
                    if (error) return [];
                    return data || [];
                } catch (e) {
                    return [];
                }
            },
            
            async addFleetVehicle(vehicleData) {
                try {
                    const { data, error } = await supabase
                        .from('fleet_vehicles')
                        .insert([vehicleData])
                        .select();
                    return { data, error };
                } catch (e) {
                    return { data: null, error: e };
                }
            },
            
            // ─── Fuel Prices ─────────────────────────────────────────────
            async getCurrentFuelPrices(region = 'National') {
                try {
                    const { data, error } = await supabase
                        .from('fuel_prices')
                        .select('*')
                        .eq('region', region)
                        .order('effective_date', { ascending: false });
                    if (error) return [];
                    return data || [];
                } catch (e) {
                    return [];
                }
            }
        };

        // ✅ Assign to global window
        window.autoV = autoVInstance;

        // ─── Add animation styles (only once) ──────────────────────────
        if (!document.getElementById('autoVStyles')) {
            const style = document.createElement('style');
            style.id = 'autoVStyles';
            style.textContent = `
                @keyframes slideIn {
                    from { opacity: 0; transform: translateX(100px); }
                    to { opacity: 1; transform: translateX(0); }
                }
                @keyframes slideOut {
                    from { opacity: 1; transform: translateX(0); }
                    to { opacity: 0; transform: translateX(100px); }
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                .spinner {
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    border: 2px solid #1e293b;
                    border-top-color: #eab308;
                    border-radius: 50%;
                    animation: spin 0.6s linear infinite;
                    margin-right: 8px;
                    vertical-align: middle;
                }
                .live-indicator {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 11px;
                    color: #22c55e;
                    background: rgba(34, 197, 94, 0.12);
                    padding: 2px 12px;
                    border-radius: 20px;
                }
                .live-indicator .dot {
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: #22c55e;
                    animation: pulse 1.5s infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.3; }
                }
                .badge-completed, .badge-active { background: #22c55e; color: #000; }
                .badge-paid { background: #8b5cf6; color: #fff; }
                .badge-pending { background: #f59e0b; color: #000; }
                .badge-processing { background: #3b82f6; color: #fff; }
                .badge-failed { background: #ef4444; color: #fff; }
                .badge-cancelled { background: #64748b; color: #fff; }
                .badge-inactive { background: #64748b; color: #fff; }
            `;
            document.head.appendChild(style);
        }

        // ─── Auto-initialize real-time subscriptions ────────────────────
        setTimeout(() => {
            if (state.listeners.length > 0) {
                subscribeToChanges();
                console.log('🔌 Real-time subscriptions active');
            }
        }, 100);

        console.log('✅ AUTO-V Supabase client initialized (Single Source of Truth + Real-time + Auth)');
    })(); // End of IIFE
}
