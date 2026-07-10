// ============================================================
// AUTO-V API CLIENT - Calls FastAPI Backend
// ============================================================

(function() {
    'use strict';

    // ─── CONFIGURATION ──────────────────────────────────────────────
    const API_BASE = 'https://auto-v.onrender.com/api/v1';
    const DEFAULT_HEADERS = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    };

    // ─── STATE ──────────────────────────────────────────────────────
    let accessToken = localStorage.getItem('access_token');
    let isRefreshing = false;
    let pendingRequests = [];

    // ─── TOAST SYSTEM ──────────────────────────────────────────────
    function showToast(message, type = 'info') {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    // ─── API REQUEST ──────────────────────────────────────────────
    async function apiRequest(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const headers = {
            ...DEFAULT_HEADERS,
            ...options.headers
        };

        if (accessToken) {
            headers['Authorization'] = `Bearer ${accessToken}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                credentials: 'include'
            });

            // Handle token refresh
            if (response.status === 401 && !options._retry) {
                const refreshed = await refreshToken();
                if (refreshed) {
                    // Retry the request with new token
                    return apiRequest(endpoint, { ...options, _retry: true });
                }
                throw new Error('Session expired. Please login again.');
            }

            if (!response.ok) {
                let errorMessage = `HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorData.message || errorMessage;
                } catch (e) {
                    errorMessage = await response.text() || errorMessage;
                }
                throw new Error(errorMessage);
            }

            return response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // ─── TOKEN REFRESH ─────────────────────────────────────────────
    async function refreshToken() {
        if (isRefreshing) {
            // Wait for the ongoing refresh
            return new Promise((resolve) => {
                pendingRequests.push(resolve);
            });
        }

        isRefreshing = true;
        try {
            const response = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Refresh failed');
            }

            const data = await response.json();
            if (data.access_token) {
                setAuthToken(data.access_token);
                // Resolve all pending requests
                pendingRequests.forEach(resolve => resolve(true));
                pendingRequests = [];
                return true;
            }
            return false;
        } catch (error) {
            console.error('Token refresh failed:', error);
            clearAuthToken();
            pendingRequests.forEach(resolve => resolve(false));
            pendingRequests = [];
            return false;
        } finally {
            isRefreshing = false;
        }
    }

    // ─── AUTH HELPERS ──────────────────────────────────────────────
    function setAuthToken(token) {
        accessToken = token;
        localStorage.setItem('access_token', token);
    }

    function getAuthToken() {
        return accessToken || localStorage.getItem('access_token');
    }

    function clearAuthToken() {
        accessToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('autoV_user');
    }

    function isAuthenticated() {
        return !!getAuthToken();
    }

    // ─── USER METHODS ─────────────────────────────────────────────
    async function getCurrentUser() {
        try {
            const token = getAuthToken();
            if (!token) return null;
            const user = await apiRequest('/auth/me');
            localStorage.setItem('autoV_user', JSON.stringify(user));
            return user;
        } catch (error) {
            if (error.message.includes('401')) {
                clearAuthToken();
            }
            return null;
        }
    }

    async function login(email, password) {
        const response = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        if (response.access_token) {
            setAuthToken(response.access_token);
        }
        return response;
    }

    async function register(data) {
        return apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async function logout() {
        try {
            if (accessToken) {
                await apiRequest('/auth/logout', { method: 'POST' });
            }
        } catch (e) {}
        clearAuthToken();
    }

    // ─── EXPOSE PUBLIC API ──────────────────────────────────────────
    const ApiClient = {
        // Config
        API_BASE: API_BASE,

        // Core
        request: apiRequest,
        get: (endpoint, options = {}) => apiRequest(endpoint, { ...options, method: 'GET' }),
        post: (endpoint, data, options = {}) => apiRequest(endpoint, { ...options, method: 'POST', body: JSON.stringify(data) }),
        put: (endpoint, data, options = {}) => apiRequest(endpoint, { ...options, method: 'PUT', body: JSON.stringify(data) }),
        delete: (endpoint, options = {}) => apiRequest(endpoint, { ...options, method: 'DELETE' }),

        // Auth
        login,
        register,
        logout,
        getCurrentUser,
        setAuthToken,
        getAuthToken,
        clearAuthToken,
        isAuthenticated,
        refreshToken,

        // Toast
        showToast
    };

    // ─── EXPOSE GLOBALLY ──────────────────────────────────────────
    if (typeof window !== 'undefined') {
        window.ApiClient = ApiClient;
        window.api = ApiClient;
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = ApiClient;
    }

    console.log('🚀 API Client initialized');
    console.log(`📌 API Base: ${API_BASE}`);

})();
