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
    let isInitialized = false;

    function showToast(message, type = 'info') {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
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

    // ─── GET CURRENT SUPABASE SESSION TOKEN ──────────────────
    // This is now the single source of truth for the bearer token.
    // No more disconnected localStorage['access_token'].
    async function getBearerToken() {
        const client = getSupabaseClient();
        if (!client) return null;

        const { data: { session }, error } = await client.auth.getSession();
        if (error) {
            console.error('Failed to get Supabase session:', error);
            return null;
        }
        return session?.access_token || null;
    }

    // ─── API REQUEST ──────────────────────────────────────────
    async function apiRequest(endpoint, options = {}) {
        const url = `${CONFIG.FASTAPI.BASE_URL}${endpoint}`;
        const token = await getBearerToken();

        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        } else {
            console.warn('[autoV.apiRequest] No Supabase session found — request will be sent without a bearer token:', endpoint);
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

    // ─── AUTH FUNCTIONS ──────────────────────────────────────
    async function getCurrentUser() {
        try {
            const token = await getBearerToken();
            if (!token) return null;
            const user = await apiRequest('/auth/me');
            return user;
        } catch (error) {
            console.error('Get current user error:', error);
            return null;
        }
    }

    async function logout() {
        try {
            await apiRequest('/auth/logout', { method: 'POST' });
        } catch (e) {}
        const client = getSupabaseClient();
        if (client) await client.auth.signOut();
        window.location.href = 'login.html';
    }

    // ─── EXPOSE PUBLIC API ──────────────────────────────────
    const autoV = {
        CONFIG: CONFIG,
        SUPABASE_URL: CONFIG.SUPABASE.URL,
        API_BASE: CONFIG.FASTAPI.BASE_URL,
        _initialized: false,
        apiRequest: apiRequest,
        checkHealth: checkHealth,
        getSupabaseClient: getSupabaseClient,
        getBearerToken: getBearerToken,
        getCurrentUser: getCurrentUser,
        logout: logout,
        showToast: showToast
    };

    autoV._initialized = true;
    isInitialized = true;

    window.autoV = autoV;

    console.log('🚀 AUTO-V API Client initialized');
    console.log(`📌 API Base: ${CONFIG.FASTAPI.BASE_URL}`);
    console.log(`📌 Health URL: ${CONFIG.FASTAPI.ROOT_URL}/health`);
    console.log(`📌 Supabase: ${CONFIG.SUPABASE.URL}`);

})();
