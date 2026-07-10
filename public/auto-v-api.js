// ============================================================
// AUTO-V HYBRID API CLIENT - Single Source of Truth
// ============================================================

(function() {
    'use strict';

    const CONFIG = {
        SUPABASE: {
            URL: 'https://tsvejnzxrxrrecgquxbq.supabase.co',
            ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ'
        },
        FASTAPI: {
            BASE_URL: 'https://auto-v.onrender.com/api/v1',
            ROOT_URL: 'https://auto-v.onrender.com'
        }
    };

    let supabaseClient = null;
    let accessToken = localStorage.getItem('access_token');
    let refreshToken = localStorage.getItem('refresh_token');
    let isRefreshing = null; // holds an in-flight refresh promise to avoid duplicate refreshes

    function showToast(message, type = 'info') {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    function getSupabaseClient() {
        if (supabaseClient) return supabaseClient;
        try {
            if (typeof window.supabase === 'undefined') {
                console.warn('Supabase client not available');
                return null;
            }
            supabaseClient = window.supabase.createClient(
                CONFIG.SUPABASE.URL,
                CONFIG.SUPABASE.ANON_KEY,
                { auth: { autoRefreshToken: true, persistSession: true }, db: { schema: 'public' } }
            );
            return supabaseClient;
        } catch (error) {
            console.error('Failed to initialize Supabase:', error);
            return null;
        }
    }

    // ─── TOKEN STORAGE (FastAPI's own tokens, from /auth/login) ─────
    function setAuthToken(token, refresh) {
        accessToken = token;
        localStorage.setItem('access_token', token);
        if (refresh) {
            refreshToken = refresh;
            localStorage.setItem('refresh_token', refresh);
        }
    }

    function clearAuthToken() {
        accessToken = null;
        refreshToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('autoV_user');
    }

    // ─── REFRESH THE ACCESS TOKEN USING /auth/refresh ────────────────
    async function refreshAccessToken() {
        if (!refreshToken) return null;

        // Avoid firing multiple simultaneous refresh calls
        if (isRefreshing) return isRefreshing;

        isRefreshing = (async () => {
            try {
                const response = await fetch(`${CONFIG.FASTAPI.BASE_URL}/auth/refresh`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: refreshToken })
                });
                if (!response.ok) throw new Error('Refresh failed');
                const data = await response.json();
                setAuthToken(data.access_token, data.refresh_token);
                return data.access_token;
            } catch (err) {
                console.error('Token refresh failed:', err);
                clearAuthToken();
                return null;
            } finally {
                isRefreshing = null;
            }
        })();

        return isRefreshing;
    }

    // ─── API REQUEST ──────────────────────────────────────────
    async function apiRequest(endpoint, options = {}, _isRetry = false) {
        const url = `${CONFIG.FASTAPI.BASE_URL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...options.headers
        };

        if (accessToken) {
            headers['Authorization'] = `Bearer ${accessToken}`;
        }

        try {
            const response = await fetch(url, { ...options, headers, credentials: 'include' });

            // If the access token expired, try refreshing once and retry the original request.
            if (response.status === 401 && !_isRetry && refreshToken) {
                const newToken = await refreshAccessToken();
                if (newToken) {
                    return apiRequest(endpoint, options, true);
                }
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

    async function checkHealth() {
        const url = `${CONFIG.FASTAPI.ROOT_URL}/health`;
        try {
            const response = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } });
            return response.ok;
        } catch (error) {
            console.warn('Health check failed:', error);
            return false;
        }
    }

    // ─── AUTH FUNCTIONS ──────────────────────────────────────
    async function getCurrentUser() {
        try {
            if (!accessToken) return null;
            return await apiRequest('/auth/me');
        } catch (error) {
            console.error('Get current user error:', error);
            if (error.message.includes('401') || error.message.toLowerCase().includes('token')) {
                clearAuthToken();
            }
            return null;
        }
    }

    async function login(email, password) {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        setAuthToken(data.access_token, data.refresh_token);
        return data;
    }

    async function logout() {
        try {
            if (accessToken) {
                await apiRequest('/auth/logout', { method: 'POST' });
            }
        } catch (e) {}
        clearAuthToken();
        window.location.href = 'login.html';
    }

    const autoV = {
        CONFIG: CONFIG,
        SUPABASE_URL: CONFIG.SUPABASE.URL,
        API_BASE: CONFIG.FASTAPI.BASE_URL,
        _initialized: false,
        apiRequest: apiRequest,
        checkHealth: checkHealth,
        getSupabaseClient: getSupabaseClient,
        getCurrentUser: getCurrentUser,
        setAuthToken: setAuthToken,
        clearAuthToken: clearAuthToken,
        login: login,
        logout: logout,
        showToast: showToast
    };

    autoV._initialized = true;
    window.autoV = autoV;

    console.log('🚀 AUTO-V API Client initialized');
    console.log(`📌 API Base: ${CONFIG.FASTAPI.BASE_URL}`);
    console.log(`📌 Health URL: ${CONFIG.FASTAPI.ROOT_URL}/health`);
    console.log(`📌 Supabase: ${CONFIG.SUPABASE.URL}`);

})();
