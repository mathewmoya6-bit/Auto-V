// ============================================================
// AUTO-V HYBRID API CLIENT - Single Source of Truth
// ============================================================

(function() {
    'use strict';

    // ─── PRODUCTION CONFIG ──────────────────────────────────────
    const CONFIG = {
        SUPABASE: {
            URL: 'https://tsvejnzxrxrrecgquxbq.supabase.co',
            ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ'
        },
        FASTAPI: {
            // Base for all versioned endpoints (auth, calculate, etc.)
            BASE_URL: 'https://auto-v.onrender.com/api/v1',
            // Root of the deployed service — health lives here, NOT under /api/v1
            ROOT_URL: 'https://auto-v.onrender.com'
        }
    };

    // ─── STATE ──────────────────────────────────────────────────
    let supabaseClient = null;
    let accessToken = localStorage.getItem('access_token');
    let isInitialized = false;

    // ─── TOAST SYSTEM ──────────────────────────────────────────
    function showToast(message, type = 'info') {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    // ─── API REQUEST ──────────────────────────────────────────
    async function apiRequest(endpoint, options = {}) {
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
            const response = await fetch(url, {
                ...options,
                headers,
                credentials: 'include'
            });

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

    // ─── HEALTH CHECK (root, not versioned) ────────────────────
    // The backend mounts /health at the app root, NOT under /api/v1,
    // unlike auth/calculate which are mounted under /api/v1.
    async function checkHealth() {
        const url = `${CONFIG.FASTAPI.ROOT_URL}/health`;
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            return response.ok;
        } catch (error) {
            console.warn('Health check failed:', error);
            return false;
        }
    }

    // ─── SUPABASE CLIENT ──────────────────────────────────────
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
                {
                    auth: {
                        autoRefreshToken: true,
                        persistSession: true
                    },
                    db: { schema: 'public' }
                }
            );
            return supabaseClient;
        } catch (error) {
            console.error('Failed to initialize Supabase:', error);
            return null;
        }
    }

    // ─── AUTH FUNCTIONS ──────────────────────────────────────
    async function getCurrentUser() {
        try {
            if (!accessToken) {
                const token = localStorage.getItem('access_token');
                if (token) {
                    accessToken = token;
                } else {
                    return null;
                }
            }

            const user = await apiRequest('/auth/me');
            return user;
        } catch (error) {
            console.error('Get current user error:', error);
            if (error.message.includes('401')) {
                clearAuthToken();
            }
            return null;
        }
    }

    function setAuthToken(token) {
        accessToken = token;
        localStorage.setItem('access_token', token);
    }

    function clearAuthToken() {
        accessToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('autoV_user');
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

    // ─── EXPOSE PUBLIC API ──────────────────────────────────
    const autoV = {
        // Config
        CONFIG: CONFIG,
        SUPABASE_URL: CONFIG.SUPABASE.URL,
        API_BASE: CONFIG.FASTAPI.BASE_URL,

        // State
        _initialized: false,

        // API Methods
        apiRequest: apiRequest,
        checkHealth: checkHealth,
        getSupabaseClient: getSupabaseClient,

        // Auth
        getCurrentUser: getCurrentUser,
        setAuthToken: setAuthToken,
        clearAuthToken: clearAuthToken,
        logout: logout,

        // Toast
        showToast: showToast
    };

    // Mark as initialized
    autoV._initialized = true;
    isInitialized = true;

    // ─── EXPOSE GLOBALLY ──────────────────────────────────
    window.autoV = autoV;

    console.log('🚀 AUTO-V API Client initialized');
    console.log(`📌 API Base: ${CONFIG.FASTAPI.BASE_URL}`);
    console.log(`📌 Health URL: ${CONFIG.FASTAPI.ROOT_URL}/health`);
    console.log(`📌 Supabase: ${CONFIG.SUPABASE.URL}`);

})();
