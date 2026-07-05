// ============================================================
// AUTO-V AUTHENTICATION MODULE
// ============================================================

(function() {
    'use strict';

    // ─── STATE ──────────────────────────────────────────────────────
    let currentUser = null;
    let authListeners = [];

    // ─── AUTH EVENT SYSTEM ──────────────────────────────────────
    function onAuthChange(callback) {
        authListeners.push(callback);
        // Immediately call with current state
        if (currentUser) {
            callback(currentUser);
        }
    }

    function notifyAuthListeners(user) {
        authListeners.forEach(callback => {
            try {
                callback(user);
            } catch (e) {
                console.error('Auth listener error:', e);
            }
        });
    }

    // ─── AUTH FUNCTIONS ──────────────────────────────────────────
    async function initAuth() {
        try {
            const user = await ApiClient.getCurrentUser();
            if (user) {
                currentUser = user;
                notifyAuthListeners(user);
                console.log('✅ User authenticated:', user.email);
            }
            return user;
        } catch (error) {
            console.warn('Auth initialization failed:', error);
            return null;
        }
    }

    async function login(email, password) {
        try {
            const response = await ApiClient.login(email, password);
            const user = await ApiClient.getCurrentUser();
            currentUser = user;
            notifyAuthListeners(user);
            return { success: true, user, response };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async function register(data) {
        try {
            const response = await ApiClient.register(data);
            return { success: true, response };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async function logout() {
        try {
            await ApiClient.logout();
            currentUser = null;
            notifyAuthListeners(null);
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async function changePassword(currentPassword, newPassword) {
        try {
            await ApiClient.post('/auth/change-password', {
                current_password: currentPassword,
                new_password: newPassword
            });
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async function resetPassword(email) {
        try {
            await ApiClient.post('/auth/reset-password', { email });
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    function getCurrentUser() {
        return currentUser;
    }

    function isAuthenticated() {
        return !!currentUser;
    }

    function isAdmin() {
        return currentUser && (currentUser.role === 'admin' || currentUser.role === 'super_admin');
    }

    function isValuer() {
        return currentUser && currentUser.role === 'valuer';
    }

    function hasRole(role) {
        return currentUser && currentUser.role === role;
    }

    // ─── PROTECTED ROUTE HELPER ──────────────────────────────────
    function requireAuth(redirectTo = 'login.html') {
        if (!isAuthenticated()) {
            window.location.href = redirectTo;
            return false;
        }
        return true;
    }

    function requireAdmin(redirectTo = 'login.html') {
        if (!isAdmin()) {
            window.location.href = redirectTo;
            return false;
        }
        return true;
    }

    // ─── EXPOSE PUBLIC API ──────────────────────────────────────────
    const Auth = {
        init: initAuth,
        login,
        register,
        logout,
        changePassword,
        resetPassword,
        getCurrentUser,
        isAuthenticated,
        isAdmin,
        isValuer,
        hasRole,
        onAuthChange,
        requireAuth,
        requireAdmin
    };

    // ─── EXPOSE GLOBALLY ──────────────────────────────────────────
    if (typeof window !== 'undefined') {
        window.Auth = Auth;
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = Auth;
    }

    console.log('🔐 Auth module initialized');

})();
