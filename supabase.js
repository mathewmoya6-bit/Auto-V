// ============================================
// AUTO-V SUPABASE - SINGLE SOURCE OF TRUTH
// ============================================

const SUPABASE_URL = "https://tsvejnzxrxrrecgquxbq.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ";
const API_BASE_URL = "https://auto-v.onrender.com";

// Initialize Supabase client
const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// ============================================
// GLOBAL AUTO-V NAMESPACE
// ============================================
window.autoV = {
    // Core
    supabase,
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    API_BASE_URL,
    
    // ========================================
    // AUTHENTICATION
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
        window.location.href = "login.html";
    },
    
    // ========================================
    // FORMATTING
    // ========================================
    formatKES(amount) {
        return new Intl.NumberFormat('en-KE', { 
            style: 'currency', 
            currency: 'KES',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    },
    
    formatDate(date, format = 'short') {
        const d = new Date(date);
        if (format === 'short') return d.toLocaleDateString('en-KE');
        if (format === 'long') return d.toLocaleDateString('en-KE', { year: 'numeric', month: 'long', day: 'numeric' });
        return d.toISOString().split('T')[0];
    },
    
    // ========================================
    // VEHICLES
    // ========================================
    async getVehicles() {
        const user = await this.getCurrentUser();
        if (!user) return [];
        const { data, error } = await supabase
            .from('vehicles')
            .select('*')
            .eq('user_id', user.id)
            .order('created_at', { ascending: false });
        if (error) return [];
        return data;
    },
    
    async registerVehicle(vehicleData) {
        const user = await this.getCurrentUser();
        if (!user) return { error: 'Not authenticated' };
        const { data, error } = await supabase
            .from('vehicles')
            .insert([{ user_id: user.id, ...vehicleData }])
            .select();
        return { data, error };
    },
    
    // ========================================
    // VALUATIONS
    // ========================================
    async calculateValuation(vehicleData) {
        try {
            const response = await fetch(${API_BASE_URL}/api/valuation/calculate, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(vehicleData)
            });
            if (response.ok) return await response.json();
        } catch (e) { console.log('API fallback'); }
        
        // Local fallback calculation
        const { make = 'Toyota', year = 2020, odometer = 50000, condition = 'Good', accident = 'None' } = vehicleData;
        const baseValues = { toyota: 2800000, mercedes: 5000000, bmw: 4500000, honda: 2500000, nissan: 2300000, default: 2000000 };
        const baseValue = baseValues[make.toLowerCase()] || baseValues.default;
        const age = new Date().getFullYear() - year;
        const ageFactor = Math.max(0.35, 1 - (age * 0.08));
        const mileageFactor = Math.max(0.45, 1 - (odometer / 300000));
        const conditionFactors = { 'Excellent': 1.15, 'Good': 1.0, 'Fair': 0.85, 'Poor': 0.7 };
        const conditionFactor = conditionFactors[condition] || 1.0;
        const accidentFactors = { 'None': 1.0, 'Minor': 0.85, 'Moderate': 0.65, 'Major': 0.4 };
        const accidentFactor = accidentFactors[accident] || 1.0;
        let marketValue = Math.round(baseValue * ageFactor * mileageFactor * conditionFactor * accidentFactor);
        marketValue = Math.max(150000, Math.min(marketValue, baseValue * 1.2));
        return {
            success: true,
            market_value: marketValue,
            insurance_value: Math.round(marketValue * 1.1),
            trade_in_value: Math.round(marketValue * 0.8),
            forced_sale_value: Math.round(marketValue * 0.7),
            certificate_number: AUTO--
        };
    },
    
    // ========================================
    // MILEAGE
    // ========================================
    async calculateMileage(data) {
        try {
            const response = await fetch(${API_BASE_URL}/api/mileage/calculate, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (response.ok) return await response.json();
        } catch (e) { console.log('API fallback'); }
        
        const rates = { 'Small Hatchback': 22, 'Compact Sedan': 28, 'Midsize Sedan': 35, 'SUV/Crossover': 42, 'Large SUV': 55, 'Pickup Truck': 48, 'Motorcycle': 12 };
        const distance = data.end_odometer - data.start_odometer;
        const rate = rates[data.vehicle_category] || 28;
        return { success: true, distance_km: distance, rate_per_km: rate, claim_amount: distance * rate };
    },
    
    async submitMileageClaim(claimData) {
        const user = await this.getCurrentUser();
        if (!user) return { error: 'Not authenticated' };
        const { data, error } = await supabase
            .from('mileage_claims')
            .insert([{ user_id: user.id, ...claimData, status: 'pending' }]);
        return { data, error };
    },
    
    // ========================================
    // UI HELPERS
    // ========================================
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.style.cssText = 
            position: fixed; bottom: 20px; right: 20px; padding: 12px 24px;
            background: ;
            color: ; border-radius: 8px;
            z-index: 9999; font-weight: 500; animation: slideIn 0.3s ease;
        ;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
};

// Add animation styles
const style = document.createElement('style');
style.textContent = 
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(100px); }
        to { opacity: 1; transform: translateX(0); }
    }
    .spinner {
        width: 40px; height: 40px;
        border: 3px solid #1e293b;
        border-top-color: #eab308;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        margin: 20px auto;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
;
document.head.appendChild(style);

console.log('✅ AUTO-V Supabase client initialized');
