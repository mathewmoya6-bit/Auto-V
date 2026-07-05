// ============================================================
// AUTO-V ADMIN MODULE - Complete
// ============================================================

(function() {
    'use strict';

    // ─── STATE ──────────────────────────────────────────────────────
    let adminData = {
        users: [],
        requests: [],
        payments: [],
        services: [],
        settings: [],
        fees: []
    };
    let stats = {};

    // ─── LOAD FUNCTIONS ──────────────────────────────────────────
    async function loadAdminData() {
        try {
            const [users, requests, payments, services, settings, fees] = await Promise.all([
                ApiClient.get('/admin/users'),
                ApiClient.get('/admin/requests'),
                ApiClient.get('/admin/payments'),
                ApiClient.get('/admin/services'),
                ApiClient.get('/admin/settings'),
                ApiClient.get('/admin/fees')
            ]);

            adminData.users = users || [];
            adminData.requests = requests || [];
            adminData.payments = payments || [];
            adminData.services = services || [];
            adminData.settings = settings || [];
            adminData.fees = fees || [];

            return adminData;
        } catch (error) {
            console.error('Failed to load admin data:', error);
            ApiClient.showToast('⚠️ Failed to load admin data', 'error');
            throw error;
        }
    }

    async function loadStats() {
        try {
            const result = await ApiClient.get('/admin/stats');
            stats = result;
            return stats;
        } catch (error) {
            console.error('Failed to load stats:', error);
            return null;
        }
    }

    async function loadFuelPrices() {
        try {
            const supabase = await getSupabaseClient();
            if (!supabase) return null;

            const { data, error } = await supabase
                .from('fuel_prices')
                .select('*')
                .order('created_at', { ascending: false })
                .limit(1);

            if (error) throw error;
            return data && data.length > 0 ? data[0] : null;
        } catch (error) {
            console.error('Failed to load fuel prices:', error);
            return null;
        }
    }

    async function saveFuelPrices(prices) {
        try {
            const supabase = await getSupabaseClient();
            if (!supabase) throw new Error('Supabase client not available');

            const { error } = await supabase
                .from('fuel_prices')
                .insert(prices);

            if (error) throw error;
            ApiClient.showToast('✅ Fuel prices saved successfully', 'success');
            return true;
        } catch (error) {
            ApiClient.showToast('❌ Failed to save fuel prices: ' + error.message, 'error');
            throw error;
        }
    }

    // ─── CRUD OPERATIONS ──────────────────────────────────────────
    async function createUser(data) {
        try {
            const result = await ApiClient.post('/admin/users', data);
            ApiClient.showToast('✅ User created successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to create user: ' + error.message, 'error');
            throw error;
        }
    }

    async function updateUser(id, data) {
        try {
            const result = await ApiClient.put(`/admin/users/${id}`, data);
            ApiClient.showToast('✅ User updated successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to update user: ' + error.message, 'error');
            throw error;
        }
    }

    async function deleteUser(id) {
        try {
            await ApiClient.delete(`/admin/users/${id}`);
            ApiClient.showToast('✅ User deleted successfully', 'success');
            return true;
        } catch (error) {
            ApiClient.showToast('❌ Failed to delete user: ' + error.message, 'error');
            throw error;
        }
    }

    async function createService(data) {
        try {
            const result = await ApiClient.post('/admin/services', data);
            ApiClient.showToast('✅ Service created successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to create service: ' + error.message, 'error');
            throw error;
        }
    }

    async function updateService(id, data) {
        try {
            const result = await ApiClient.put(`/admin/services/${id}`, data);
            ApiClient.showToast('✅ Service updated successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to update service: ' + error.message, 'error');
            throw error;
        }
    }

    async function deleteService(id) {
        try {
            await ApiClient.delete(`/admin/services/${id}`);
            ApiClient.showToast('✅ Service deleted successfully', 'success');
            return true;
        } catch (error) {
            ApiClient.showToast('❌ Failed to delete service: ' + error.message, 'error');
            throw error;
        }
    }

    async function updateSetting(key, value) {
        try {
            const result = await ApiClient.put(`/admin/settings/${key}`, { value });
            ApiClient.showToast('✅ Setting updated successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to update setting: ' + error.message, 'error');
            throw error;
        }
    }

    async function updateFee(id, fee) {
        try {
            const result = await ApiClient.put(`/admin/fees/${id}`, { fee });
            ApiClient.showToast('✅ Fee updated successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('❌ Failed to update fee: ' + error.message, 'error');
            throw error;
        }
    }

    // ─── EXPORT FUNCTIONS ──────────────────────────────────────────
    function exportData(type) {
        let data = [];
        let headers = [];

        switch (type) {
            case 'users':
                headers = ['ID', 'Name', 'Email', 'Role', 'Status', 'Joined'];
                data = adminData.users.map(u => [
                    u.id,
                    u.full_name || 'N/A',
                    u.email || 'N/A',
                    u.role || 'user',
                    u.is_active ? 'Active' : 'Inactive',
                    formatDate(u.created_at)
                ]);
                break;
            case 'requests':
                headers = ['ID', 'User', 'Service', 'Amount', 'Status', 'Date'];
                data = adminData.requests.map(r => [
                    r.id,
                    r.customer_name || r.user_email || 'Unknown',
                    r.service_type || 'N/A',
                    r.amount || 0,
                    r.status || 'pending',
                    formatDate(r.created_at)
                ]);
                break;
            case 'payments':
                headers = ['User', 'Amount', 'Method', 'Status', 'Date', 'Reference'];
                data = adminData.payments.map(p => [
                    p.user_name || p.user_email || 'Unknown',
                    p.amount || 0,
                    p.payment_method || 'M-Pesa',
                    p.status || 'pending',
                    formatDate(p.created_at),
                    p.transaction_id || p.reference || '—'
                ]);
                break;
            default:
                return;
        }

        if (!data.length) {
            ApiClient.showToast('No data to export', 'info');
            return;
        }

        downloadCSV([headers, ...data], `auto_v_${type}_${Date.now()}.csv`);
        ApiClient.showToast('📤 Data exported successfully', 'success');
    }

    // ─── GET SUPABASE CLIENT ──────────────────────────────────────
    function getSupabaseClient() {
        if (typeof window.supabase !== 'undefined') {
            return window.supabase;
        }
        return null;
    }

    // ─── EXPOSE PUBLIC API ──────────────────────────────────────────
    const Admin = {
        // Load
        loadAdminData,
        loadStats,
        loadFuelPrices,
        saveFuelPrices,

        // Data
        getData: () => adminData,
        getStats: () => stats,

        // CRUD
        createUser,
        updateUser,
        deleteUser,
        createService,
        updateService,
        deleteService,
        updateSetting,
        updateFee,

        // Export
        exportData
    };

    // ─── EXPOSE GLOBALLY ──────────────────────────────────────────
    if (typeof window !== 'undefined') {
        window.Admin = Admin;
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = Admin;
    }

    console.log('⚙️ Admin module initialized');

})();
