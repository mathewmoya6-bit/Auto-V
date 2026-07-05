// ============================================================
// AUTO-V ADMIN MODULE
// ============================================================

(function() {
    'use strict';

    // ─── STATE ──────────────────────────────────────────────────────
    let adminData = {
        users: [],
        requests: [],
        payments: [],
        services: [],
        settings: []
    };

    // ─── LOAD FUNCTIONS ──────────────────────────────────────────
    async function loadAdminData() {
        try {
            const [users, requests, payments, services, settings] = await Promise.all([
                ApiClient.get('/admin/users'),
                ApiClient.get('/admin/requests'),
                ApiClient.get('/admin/payments'),
                ApiClient.get('/admin/services'),
                ApiClient.get('/admin/settings')
            ]);

            adminData.users = users || [];
            adminData.requests = requests || [];
            adminData.payments = payments || [];
            adminData.services = services || [];
            adminData.settings = settings || [];

            return adminData;
        } catch (error) {
            console.error('Failed to load admin data:', error);
            ApiClient.showToast('Failed to load admin data', 'error');
            throw error;
        }
    }

    async function loadStats() {
        try {
            const stats = await ApiClient.get('/admin/stats');
            return stats;
        } catch (error) {
            console.error('Failed to load stats:', error);
            return null;
        }
    }

    // ─── CRUD OPERATIONS ──────────────────────────────────────────
    async function createUser(data) {
        try {
            const result = await ApiClient.post('/admin/users', data);
            ApiClient.showToast('User created successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to create user: ' + error.message, 'error');
            throw error;
        }
    }

    async function updateUser(id, data) {
        try {
            const result = await ApiClient.put(`/admin/users/${id}`, data);
            ApiClient.showToast('User updated successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to update user: ' + error.message, 'error');
            throw error;
        }
    }

    async function deleteUser(id) {
        try {
            await ApiClient.delete(`/admin/users/${id}`);
            ApiClient.showToast('User deleted successfully', 'success');
            return true;
        } catch (error) {
            ApiClient.showToast('Failed to delete user: ' + error.message, 'error');
            throw error;
        }
    }

    async function createService(data) {
        try {
            const result = await ApiClient.post('/admin/services', data);
            ApiClient.showToast('Service created successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to create service: ' + error.message, 'error');
            throw error;
        }
    }

    async function updateService(id, data) {
        try {
            const result = await ApiClient.put(`/admin/services/${id}`, data);
            ApiClient.showToast('Service updated successfully', 'success');
            return result;
        } catch (error) {
            ApiClient.showToast('Failed to update service: ' + error.message, 'error');
            throw error;
        }
    }

    async function deleteService(id) {
        try {
            await ApiClient.delete(`/admin/services/${id}`);
            ApiClient.showToast('Service deleted successfully', 'success');
            return true;
        } catch (error) {
            ApiClient.showToast('Failed to delete service: ' + error.message, 'error');
            throw error;
        }
    }

    async function updateSetting(key, value) {
        try {
            const result = await ApiClient.put(`/admin/settings/${key}`, { value });
            ApiClient.showToast('Setting updated successfully', 'success');
            return result;
        } catch (error) {
           
