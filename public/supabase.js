// ============================================
// AUTO-V API CLIENT CONFIGURATION
// Hybrid Architecture: Supabase + FastAPI
// ============================================

// ✅ GUARD: Prevent double initialization
if (window.autoV && window.autoV._initialized) {
    console.log('✅ AUTO-V API already initialized, skipping...');
} else {
    (function() {
        'use strict';

        // ─── PRODUCTION CONFIG ──────────────────────────────────────────
        // Supabase (Single Source of Truth for data)
        const SUPABASE_URL = 'https://tsvejnzxrxrrecgquxbq.supabase.co';
        const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ';

        // FastAPI (Business Logic - Calculations, Claims, Auth)
        const API_BASE = 'https://auto-v.onrender.com/api/v1';

        // ─── State ──────────────────────────────────────────────────────
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
            categories: [],
            variants: [],
            routes: [],
            lastUpdated: null,
            listeners: [],
            isSupabaseConnected: false
        };

        // ─── Supabase Client ──────────────────────────────────────────
        // Load Supabase JS from CDN if not already loaded
        let supabaseClient = null;

        async function getSupabaseClient() {
            if (supabaseClient) return supabaseClient;
            
            try {
                // Check if supabase is already loaded
                if (window.supabase) {
                    supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
                    console.log('🔗 Supabase client initialized');
                    return supabaseClient;
                }

                // Dynamically load Supabase JS
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
                    script.onload = resolve;
                    script.onerror = reject;
                    document.head.appendChild(script);
                });

                supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
                console.log('🔗 Supabase client loaded and initialized');
                return supabaseClient;
            } catch (error) {
                console.error('❌ Failed to initialize Supabase client:', error);
                return null;
            }
        }

        // ─── Supabase Data Fetching (Single Source of Truth) ──────────
        async function fetchCategoriesFromSupabase() {
            try {
                const supabase = await getSupabaseClient();
                if (!supabase) throw new Error('Supabase client not available');

                const { data, error } = await supabase
                    .from('vehicle_categories')
                    .select(`
                        id,
                        name,
                        fuel_type,
                        is_active,
                        vehicle_variants (
                            id,
                            label,
                            fixed_per_km,
                            operating_per_km,
                            total_per_km,
                            initial_cost,
                            year1,
                            year2,
                            year3,
                            year4,
                            year5,
                            components,
                            is_active
                        )
                    `)
                    .eq('is_active', true)
                    .order('name', { ascending: true });

                if (error) throw error;
                
                state.categories = data || [];
                state.isSupabaseConnected = true;
                return state.categories;
            } catch (error) {
                console.warn('⚠️ Supabase categories fetch failed:', error.message);
                return state.categories;
            }
        }

        async function fetchRoutesFromSupabase() {
            try {
                const supabase = await getSupabaseClient();
                if (!supabase) throw new Error('Supabase client not available');

                const { data, error } = await supabase
                    .from('routes')
                    .select('*')
                    .eq('is_active', true)
                    .order('from_city', { ascending: true });

                if (error) throw error;
                
                state.routes = data || [];
                return state.routes;
            } catch (error) {
                console.warn('⚠️ Supabase routes fetch failed:', error.message);
                return state.routes;
            }
        }

        async function fetchAllFromSupabase() {
            await Promise.all([
                fetchCategoriesFromSupabase(),
                fetchRoutesFromSupabase()
            ]);
            notifyListeners();
            return { categories: state.categories, routes: state.routes };
        }

        // ─── Token Management ──────────────────────────────────────────
        function getAuthToken() {
            return localStorage.getItem('access_token');
        }

        function setAuthToken(token) {
            localStorage.setItem('access_token', token);
        }

        function clearAuthToken() {
            localStorage.removeItem('access_token');
        }

        function getAuthHeaders() {
            const token = getAuthToken();
            return {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` })
            };
        }

        // ─── FastAPI Request Helper (Business Logic) ──────────────────
        async function apiRequest(endpoint, options = {}) {
            const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
            const config = {
                ...options,
                headers: {
                    ...getAuthHeaders(),
                    ...(options.headers || {})
                }
            };

            try {
                const response = await fetch(url, config);
                
                if (response.status === 401) {
                    clearAuthToken();
                    if (!window.location.pathname.includes('login.html') && 
                        !window.location.pathname.includes('admin-login.html')) {
                        window.location.href = 'login.html';
                    }
                    throw new Error('Session expired. Please login again.');
                }

                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.detail || data.error || `HTTP ${response.status}`);
                    }
                    return data;
                } else {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response;
                }
            } catch (error) {
                if (error.message.includes('fetch')) {
                    throw new Error('Network error. Please check your connection.');
                }
                throw error;
            }
        }

        // ─── Data Fetching (Supabase + FastAPI) ──────────────────────
        async function fetchFees() {
            try {
                const data = await apiRequest('/admin/settings?keys=instant_fee,valuation_fee,inspection_fee,assessment_fee,mileage_fee,fleet_fee,verification_fee,professional_fee');
                
                if (data && Array.isArray(data)) {
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
                
                return state.fees;
            } catch (err) {
                console.warn('⚠️ Could not fetch fees:', err.message);
                return state.fees;
            }
        }

        async function fetchStats() {
            try {
                const stats = await apiRequest('/admin/stats');
                
                state.stats = {
                    users: stats.total_users || 0,
                    requests: stats.total_requests || 0,
                    revenue: stats.total_revenue || 0,
                    pending: stats.pending_payments || 0,
                    instant: stats.instant_requests || 0,
                    vehicles: stats.total_vehicles || 0,
                    inspections: stats.total_inspections || 0
                };
                state.lastUpdated = new Date();
                
                return state.stats;
            } catch (err) {
                console.warn('⚠️ Could not fetch stats:', err.message);
                return state.stats;
            }
        }

        async function fetchAllData() {
            // Fetch from Supabase (data) and FastAPI (business logic)
            await Promise.all([
                fetchAllFromSupabase(),
                fetchFees(),
                fetchStats()
            ]);
            notifyListeners();
            return { 
                categories: state.categories, 
                routes: state.routes,
                fees: state.fees, 
                stats: state.stats 
            };
        }

        // ─── Listener System ────────────────────────────────────────────
        function addListener(callback) {
            if (typeof callback === 'function') {
                state.listeners.push(callback);
                try {
                    callback({ 
                        categories: state.categories, 
                        routes: state.routes,
                        fees: state.fees, 
                        stats: state.stats 
                    });
                } catch (err) {
                    console.warn('Listener error:', err);
                }
            }
        }

        function removeListener(callback) {
            state.listeners = state.listeners.filter(cb => cb !== callback);
        }

        function notifyListeners() {
            state.listeners.forEach(cb => {
                try {
                    cb({ 
                        categories: state.categories, 
                        routes: state.routes,
                        fees: state.fees, 
                        stats: state.stats 
                    });
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
            SUPABASE_URL: SUPABASE_URL,
            API_BASE: API_BASE,
            state: state,
            _initialized: true,
            
            // ─── Supabase Methods (Single Source of Truth) ─────────────
            getSupabaseClient: getSupabaseClient,
            fetchCategoriesFromSupabase: fetchCategoriesFromSupabase,
            fetchRoutesFromSupabase: fetchRoutesFromSupabase,
            fetchAllFromSupabase: fetchAllFromSupabase,
            
            // ─── FastAPI Methods (Business Logic) ──────────────────────
            apiRequest: apiRequest,
            getAuthToken: getAuthToken,
            setAuthToken: setAuthToken,
            clearAuthToken: clearAuthToken,
            getAuthHeaders: getAuthHeaders,
            
            // ─── Data Functions ──────────────────────────────────────────
            fetchFees: fetchFees,
            fetchStats: fetchStats,
            fetchAllData: fetchAllData,
            refresh: fetchAllData,
            
            // ─── Real-time Sync ──────────────────────────────────────────
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
                    const token = getAuthToken();
                    if (!token) return null;
                    
                    const user = await apiRequest('/auth/me');
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
                try {
                    await apiRequest('/auth/logout', { method: 'POST' });
                } catch (e) {}
                clearAuthToken();
                localStorage.clear();
                sessionStorage.clear();
                window.location.href = "login.html";
            },
            
            // ─── USER PROFILE ──────────────────────────────────────────
            async upsertUserProfile(userId, email, role) {
                try {
                    const data = await apiRequest('/users/profile', {
                        method: 'PUT',
                        body: JSON.stringify({
                            user_id: userId,
                            full_name: email?.split('@')[0] || 'User',
                            email: email,
                            role: role || 'individual'
                        })
                    });
                    return { data, error: null };
                } catch (err) {
                    console.warn('Error upserting user profile:', err.message);
                    return { data: null, error: err };
                }
            },
            
            async getUserRole(userId) {
                try {
                    const profile = await apiRequest(`/users/profile/${userId}`);
                    return profile?.role || 'individual';
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
                    const data = await apiRequest('/service-requests', {
                        method: 'POST',
                        body: JSON.stringify({
                            user_id: user.id,
                            ...requestData,
                            payment_status: 'paid',
                            status: 'completed'
                        })
                    });
                    return { data, error: null };
                } catch (e) {
                    return { data: null, error: e };
                }
            },
            
            async getUserServiceHistory() {
                const user = await this.getCurrentUser();
                if (!user) return [];
                try {
                    const data = await apiRequest('/service-requests');
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
            
            // ─── Mileage (Using Supabase Data + FastAPI Calculation) ──
            async getMileageRate(vehicleCategory) {
                if (!vehicleCategory) return 25;
                try {
                    const rates = await apiRequest('/mileage/rates');
                    const rate = rates.find(r => r.vehicle_category === vehicleCategory && r.is_active);
                    return rate?.rate_per_km || 25;
                } catch (e) {
                    return 25;
                }
            },
            
            async getAllMileageRates() {
                try {
                    const data = await apiRequest('/mileage/rates');
                    return data || [];
                } catch (e) {
                    return [];
                }
            },
            
            async submitMileageClaim(claimData) {
                const user = await this.getCurrentUser();
                if (!user) return { error: 'Not authenticated' };
                
                try {
                    const data = await apiRequest('/mileage/claims', {
                        method: 'POST',
                        body: JSON.stringify({
                            user_id: user.id,
                            employee_name: user.full_name || user.email?.split('@')[0] || 'Employee',
                            ...claimData,
                            status: 'pending'
                        })
                    });
                    return { data, error: null };
                } catch (e) {
                    return { data: null, error: e };
                }
            },
            
            async getUserMileageClaims() {
                const user = await this.getCurrentUser();
                if (!user) return [];
                try {
                    const data = await apiRequest('/mileage/claims');
                    return data || [];
                } catch (e) {
                    return [];
                }
            },
            
            async cancelMileageClaim(claimId) {
                try {
                    await apiRequest(`/mileage/claims/${claimId}`, { method: 'DELETE' });
                    return { success: true, error: null };
                } catch (e) {
                    return { success: false, error: e };
                }
            },
            
            // ─── Fleet ───────────────────────────────────────────────────
            async getFleetVehicles(organizationId = null) {
                try {
                    let endpoint = '/fleet/vehicles';
                    if (organizationId) {
                        endpoint += `?organization_id=${organizationId}`;
                    }
                    const data = await apiRequest(endpoint);
                    return data || [];
                } catch (e) {
                    return [];
                }
            },
            
            async addFleetVehicle(vehicleData) {
                try {
                    const data = await apiRequest('/fleet/vehicles', {
                        method: 'POST',
                        body: JSON.stringify(vehicleData)
                    });
                    return { data, error: null };
                } catch (e) {
                    return { data: null, error: e };
                }
            },
            
            // ─── Fuel Prices ─────────────────────────────────────────────
            async getCurrentFuelPrices(region = 'National') {
                try {
                    const data = await apiRequest(`/fuel/prices?region=${encodeURIComponent(region)}`);
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

        // ─── Auto-initialize ──────────────────────────────────────────
        setTimeout(async () => {
            try {
                // Load Supabase data
                await fetchAllFromSupabase();
                console.log('📊 Supabase data loaded:', {
                    categories: state.categories.length,
                    routes: state.routes.length
                });

                // If authenticated, fetch business data
                if (getAuthToken()) {
                    await Promise.all([fetchFees(), fetchStats()]);
                    console.log('📊 Business data loaded');
                }
            } catch (error) {
                console.warn('⚠️ Auto-initialization warning:', error.message);
            }
        }, 100);

        console.log('✅ AUTO-V API client initialized (Hybrid: Supabase + FastAPI)');
        console.log(`🔗 Supabase URL: ${SUPABASE_URL}`);
        console.log(`🔗 FastAPI URL: ${API_BASE}`);

    })(); // End of IIFE
}
