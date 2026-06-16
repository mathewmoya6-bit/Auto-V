// ============================================
// AUTO-V SUPABASE - PRODUCTION
// ============================================

const SUPABASE_URL = "https://tsvejnzxrxrrecgquxbq.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ";
const API_BASE_URL = "https://auto-v.onrender.com";

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

window.autoV = {
    supabase,
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    API_BASE_URL,

    // ========================================
    // AUTHENTICATION - PRODUCTION
    // ========================================
    async getCurrentUser() {
        const { data: { user }, error } = await supabase.auth.getUser();
        if (error || !user) return null;
        return user;
    },

    async requireAuth() {
        const user = await this.getCurrentUser();
        if (!user) { window.location.href = "login.html"; return null; }
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
        return new Intl.NumberFormat('en-KE', { style: 'currency', currency: 'KES', minimumFractionDigits: 0 }).format(amount || 0);
    },

    formatDate(date) {
        return new Date(date).toLocaleDateString('en-KE', { year: 'numeric', month: 'short', day: 'numeric' });
    },

    // ========================================
    // TOAST NOTIFICATION
    // ========================================
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        const colors = { success: '#22c55e', error: '#ef4444', warning: '#eab308', info: '#3b82f6' };
        toast.style.cssText = 
            position: fixed; bottom: 20px; right: 20px; padding: 12px 24px;
            background: ; color: ;
            border-radius: 8px; z-index: 9999; font-weight: 500;
            animation: slideIn 0.3s ease; max-width: 400px;
        ;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    },

    // ========================================
    // VEHICLES
    // ========================================
    async getVehicles() {
        const user = await this.getCurrentUser();
        if (!user) return [];
        const { data, error } = await supabase.from('vehicles').select('*').eq('user_id', user.id).order('created_at', { ascending: false });
        return error ? [] : data;
    },

    async registerVehicle(data) {
        const user = await this.getCurrentUser();
        if (!user) return { error: 'Not authenticated' };
        return await supabase.from('vehicles').insert([{ user_id: user.id, ...data }]).select();
    },

    // ========================================
    // VALUATIONS
    // ========================================
    async calculateValuation(data) {
        try {
            const res = await fetch(${API_BASE_URL}/api/valuation/calculate, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) return await res.json();
        } catch(e) { console.log('API fallback'); }
        // Local fallback
        const { make = 'Toyota', year = 2020, odometer = 50000, condition = 'Good', accident = 'None' } = data;
        const base = { toyota: 2800000, mercedes: 5000000, bmw: 4500000, honda: 2500000, nissan: 2300000 };
        const baseValue = base[make.toLowerCase()] || 2000000;
        const age = new Date().getFullYear() - year;
        const ageFactor = Math.max(0.35, 1 - age * 0.08);
        const mileageFactor = Math.max(0.45, 1 - odometer / 300000);
        const cond = { Excellent: 1.15, Good: 1.0, Fair: 0.85, Poor: 0.7 };
        const acc = { None: 1.0, Minor: 0.85, Moderate: 0.65, Major: 0.4 };
        let value = Math.round(baseValue * ageFactor * mileageFactor * (cond[condition] || 1) * (acc[accident] || 1));
        value = Math.max(150000, Math.min(value, baseValue * 1.2));
        return { success: true, market_value: value, insurance_value: Math.round(value * 1.1), trade_in_value: Math.round(value * 0.8), forced_sale_value: Math.round(value * 0.7), certificate_number: AUTO-- };
    },

    async saveValuation(data) {
        const user = await this.getCurrentUser();
        if (!user) return { error: 'Not authenticated' };
        return await supabase.from('valuations').insert([{ user_id: user.id, ...data }]).select();
    },

    // ========================================
    // MILEAGE
    // ========================================
    async calculateMileage(data) {
        try {
            const res = await fetch(${API_BASE_URL}/api/mileage/calculate, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) return await res.json();
        } catch(e) { console.log('API fallback'); }
        const rates = { 'Small Hatchback': 22, 'Compact Sedan': 28, 'Midsize Sedan': 35, 'SUV/Crossover': 42, 'Large SUV': 55, 'Pickup Truck': 48, 'Motorcycle': 12 };
        const distance = data.end_odometer - data.start_odometer;
        const rate = rates[data.vehicle_category] || 28;
        return { success: true, distance_km: distance, rate_per_km: rate, claim_amount: distance * rate };
    },

    async submitMileageClaim(data) {
        const user = await this.getCurrentUser();
        if (!user) return { error: 'Not authenticated' };
        return await supabase.from('mileage_claims').insert([{ user_id: user.id, ...data, status: 'pending' }]).select();
    },

    // ========================================
    // ADMIN
    // ========================================
    async getAdminStats() {
        const [users, valuations, inspections, claims] = await Promise.all([
            supabase.from('user_profiles').select('*', { count: 'exact' }),
            supabase.from('valuations').select('*', { count: 'exact' }),
            supabase.from('inspections').select('*', { count: 'exact' }),
            supabase.from('mileage_claims').select('*', { count: 'exact' })
        ]);
        return {
            users: users.count || 0,
            valuations: valuations.count || 0,
            inspections: inspections.count || 0,
            claims: claims.count || 0
        };
    },

    async getPendingClaims() {
        const { data, error } = await supabase.from('mileage_claims').select('*').eq('status', 'pending').order('trip_date', { ascending: false });
        return error ? [] : data;
    },

    async approveClaim(claimId) {
        return await supabase.from('mileage_claims').update({ status: 'approved', approval_date: new Date().toISOString() }).eq('id', claimId);
    },

    async rejectClaim(claimId) {
        return await supabase.from('mileage_claims').update({ status: 'rejected' }).eq('id', claimId);
    },

    async getMileageRates() {
        const { data, error } = await supabase.from('mileage_rates').select('*').eq('is_active', true).order('rate_per_km');
        return error ? [] : data;
    },

    async addMileageRate(data) {
        return await supabase.from('mileage_rates').insert([{ ...data, is_active: true }]).select();
    },

    async deactivateMileageRate(id) {
        return await supabase.from('mileage_rates').update({ is_active: false }).eq('id', id);
    },

    async getSystemSettings() {
        const { data, error } = await supabase.from('system_settings').select('*');
        const settings = {};
        if (data) data.forEach(s => settings[s.setting_key] = s.setting_value);
        return settings;
    },

    async updateSystemSetting(key, value) {
        return await supabase.from('system_settings').upsert({ setting_key: key, setting_value: value.toString(), updated_at: new Date().toISOString() });
    }
};

// Add styles
const style = document.createElement('style');
style.textContent = 
    @keyframes slideIn { from { opacity:0; transform:translateX(100px); } to { opacity:1; transform:translateX(0); } }
    .spinner { width:40px; height:40px; border:3px solid #1e293b; border-top-color:#eab308; border-radius:50%; animation:spin 0.8s linear infinite; margin:20px auto; }
    @keyframes spin { to { transform:rotate(360deg); } }
;
document.head.appendChild(style);

console.log('✅ AUTO-V Production initialized');
