// ============================================
// AUTO-V SUPABASE CONFIGURATION
// Single Source of Truth
// ============================================

(function() {
    // ─── Check if already initialized ──────────────────────────────
    if (window.autoV && window.autoV.supabase) {
        console.log('✅ AUTO-V Supabase already initialized, skipping...');
        return;
    }

    // ─── Configuration ──────────────────────────────────────────────
    const SUPABASE_URL = "https://tsvejnzxrxrrecgquxbq.supabase.co";
    const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ";

    // ─── Create Supabase client ──────────────────────────────────────
    // Check if window.supabase exists (from CDN)
    if (typeof window.supabase === 'undefined' || !window.supabase.createClient) {
        console.error('❌ Supabase CDN not loaded. Please check the script tag.');
        return;
    }

    const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    console.log('✅ Supabase client created');

    // ============================================
    // GLOBAL AUTO-V NAMESPACE
    // ============================================
    window.autoV = {
        // Core
        supabase: supabase,
        SUPABASE_URL: SUPABASE_URL,
        SUPABASE_ANON_KEY: SUPABASE_ANON_KEY,
        
        // ========================================
        // AUTHENTICATION HELPERS
        // ========================================
        async getCurrentUser() {
            const { data: { user }, error } = await supabase.auth.getUser();
            if (error || !user) return null;
            return user;
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
            localStorage.removeItem('autoV_user');
            window.location.href = "login.html";
        },
        
        // ========================================
        // FORMATTING HELPERS
        // ========================================
        formatKES(amount) {
            return new Intl.NumberFormat('en-KE', { 
                style: 'currency', 
                currency: 'KES',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(amount);
        },
        
        formatDate(date, format = 'short') {
            const d = new Date(date);
            if (format === 'short') return d.toLocaleDateString('en-KE');
            if (format === 'long') return d.toLocaleDateString('en-KE', { year: 'numeric', month: 'long', day: 'numeric' });
            if (format === 'datetime') return d.toLocaleString('en-KE');
            return d.toISOString().split('T')[0];
        },
        
        formatNumber(num) {
            return num?.toLocaleString('en-KE') || '0';
        },
        
        // ========================================
        // UI HELPERS
        // ========================================
        showToast(message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            toast.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                padding: 12px 24px;
                background: ${type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : '#eab308'};
                color: ${type === 'success' ? '#000' : '#fff'};
                border-radius: 8px;
                z-index: 9999;
                font-weight: 500;
                animation: slideIn 0.3s ease;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            `;
            document.body.appendChild(toast);
            setTimeout(() => {
                toast.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        },
        
        showLoading(elementId, show = true) {
            const el = document.getElementById(elementId);
            if (!el) return;
            if (show) {
                el.innerHTML = '<div class="spinner"></div>';
                el.style.opacity = '0.5';
            } else {
                el.style.opacity = '1';
            }
        },
        
        // ========================================
        // USER PROFILE HELPERS
        // ========================================
        async upsertUserProfile(userId, email, name, phone) {
            try {
                const { error } = await supabase
                    .from('user_profiles')
                    .upsert({
                        id: userId,
                        email: email,
                        full_name: name || email.split('@')[0],
                        phone: phone || '',
                        first_login: true,
                        has_vehicle: false,
                        login_count: 1,
                        updated_at: new Date().toISOString()
                    }, { onConflict: 'id' });
                
                if (error) {
                    console.warn('Error upserting user profile:', error.message);
                }
            } catch (err) {
                console.warn('Error in upsertUserProfile:', err);
            }
        },
        
        async checkFirstTimeUser(userId) {
            try {
                const { data, error } = await supabase
                    .from('user_profiles')
                    .select('first_login, has_vehicle, login_count, full_name, phone')
                    .eq('id', userId)
                    .single();
                
                if (error) {
                    console.warn('User profile query failed, treating as first-time user:', error.message);
                    return true;
                }
                
                if (!data) return true;
                if (!data.full_name || !data.phone) return true;
                return !(data.first_login === false && data.has_vehicle === true && data.login_count >= 2);
            } catch (err) {
                console.warn('Error checking user profile, treating as first-time user:', err);
                return true;
            }
        },
        
        async isProfileComplete(userId) {
            try {
                const { data, error } = await supabase
                    .from('user_profiles')
                    .select('full_name, phone')
                    .eq('id', userId)
                    .single();
                
                if (error) {
                    console.warn('Profile completeness query failed, assuming incomplete:', error.message);
                    return false;
                }
                
                return !!(data && data.full_name && data.phone);
            } catch (err) {
                console.warn('Error checking profile completeness:', err);
                return false;
            }
        },
        
        // ========================================
        // MILEAGE HELPERS
        // ========================================
        async getMileageRate(vehicleCategory) {
            if (!vehicleCategory) return 25;
            const { data, error } = await supabase
                .from('mileage_rates')
                .select('rate_per_km')
                .eq('vehicle_category', vehicleCategory)
                .eq('is_active', true)
                .single();
            if (error || !data) return 25;
            return data.rate_per_km;
        },
        
        async getAllMileageRates() {
            const { data, error } = await supabase
                .from('mileage_rates')
                .select('*')
                .eq('is_active', true)
                .order('rate_per_km');
            if (error) return [];
            return data;
        },
        
        async submitMileageClaim(claimData) {
            const user = await this.getCurrentUser();
            if (!user) return { error: 'Not authenticated' };
            
            const { data, error } = await supabase
                .from('mileage_claims')
                .insert([{
                    user_id: user.id,
                    employee_name: user.email?.split('@')[0] || 'Employee',
                    ...claimData,
                    status: 'pending'
                }]);
            return { data, error };
        },
        
        async getUserMileageClaims() {
            const user = await this.getCurrentUser();
            if (!user) return [];
            const { data, error } = await supabase
                .from('mileage_claims')
                .select('*')
                .eq('user_id', user.id)
                .order('trip_date', { ascending: false });
            if (error) return [];
            return data;
        },
        
        async cancelMileageClaim(claimId) {
            const { error } = await supabase
                .from('mileage_claims')
                .delete()
                .eq('id', claimId);
            return { success: !error, error };
        },
        
        // ========================================
        // VALUATION HELPERS
        // ========================================
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
        
        async saveServiceRequest(requestData) {
            const user = await this.getCurrentUser();
            if (!user) return { error: 'Not authenticated' };
            
            const { data, error } = await supabase
                .from('service_requests')
                .insert([{
                    user_id: user.id,
                    ...requestData,
                    payment_status: 'paid',
                    status: 'completed',
                    created_at: new Date().toISOString()
                }]);
            return { data, error };
        },
        
        async getUserServiceHistory() {
            const user = await this.getCurrentUser();
            if (!user) return [];
            const { data, error } = await supabase
                .from('service_requests')
                .select('*')
                .eq('user_id', user.id)
                .order('created_at', { ascending: false });
            if (error) return [];
            return data;
        },
        
        // ========================================
        // FLEET HELPERS
        // ========================================
        async getFleetVehicles(organizationId = null) {
            let query = supabase.from('fleet_vehicles').select('*');
            if (organizationId) query = query.eq('organization_id', organizationId);
            const { data, error } = await query;
            if (error) return [];
            return data;
        },
        
        async addFleetVehicle(vehicleData) {
            const { data, error } = await supabase
                .from('fleet_vehicles')
                .insert([vehicleData]);
            return { data, error };
        },
        
        // ========================================
        // FUEL PRICE HELPERS
        // ========================================
        async getCurrentFuelPrices(region = 'National') {
            const { data, error } = await supabase
                .from('fuel_prices')
                .select('*')
                .eq('region', region)
                .order('effective_date', { ascending: false });
            if (error) return [];
            return data;
        },
        
        // ========================================
        // REPORT GENERATION
        // ========================================
        generateReportHTML(type, data) {
            if (type === 'valuation') {
                return `
                    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                        <div style="text-align: center; border-bottom: 2px solid #eab308; padding-bottom: 20px;">
                            <h1 style="color: #eab308;">AUTO-V Valuation Report</h1>
                            <p>Certificate: ${data.certificate_number}</p>
                            <p>Date: ${this.formatDate(new Date(), 'long')}</p>
                        </div>
                        <div style="margin: 20px 0;">
                            <h3>Vehicle Details</h3>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Make:</strong></td><td>${data.make}</td></tr>
                                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Model:</strong></td><td>${data.model}</td></tr>
                                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Year:</strong></td><td>${data.year}</td></tr>
                                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Registration:</strong></td><td>${data.registration_number}</td></tr>
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
        }
    };

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
            .spinner {
                width: 40px;
                height: 40px;
                border: 3px solid #1e293b;
                border-top-color: #eab308;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }

    console.log('✅ AUTO-V Supabase client initialized (Single Source of Truth)');
})();
