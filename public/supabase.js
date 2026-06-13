// supabase.js - Single source of truth for all AUTO-V pages
const SUPABASE_URL = "https://tsvejnzxrxrrecgquxbq.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ";

// Create Supabase client
const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Global state
let currentUser = null;
let isAuthenticated = false;

// Authentication functions
async function getCurrentUser() {
    try {
        const { data: { user }, error } = await supabase.auth.getUser();
        if (error) throw error;
        currentUser = user;
        isAuthenticated = !!user;
        return user;
    } catch (e) {
        console.error('Auth error:', e);
        return null;
    }
}

async function requireAuth() {
    const user = await getCurrentUser();
    if (!user) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

async function logout() {
    try {
        await supabase.auth.signOut();
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = 'index.html';
    } catch (e) {
        console.error('Logout error:', e);
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = 'index.html';
    }
}

// Service request functions
async function createServiceRequest(data) {
    const { data: result, error } = await supabase
        .from('service_requests')
        .insert(data)
        .select()
        .single();
    
    if (error) throw error;
    return result;
}

async function getServiceRequests(userId) {
    const { data, error } = await supabase
        .from('service_requests')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false });
    
    if (error) throw error;
    return data;
}

async function getServiceRequest(id) {
    const { data, error } = await supabase
        .from('service_requests')
        .select('*')
        .eq('id', id)
        .single();
    
    if (error) throw error;
    return data;
}

// Realtime subscription
function subscribeToUpdates(userId, callback) {
    return supabase
        .channel('service_requests_updates')
        .on('postgres_changes', {
            event: '*',
            schema: 'public',
            table: 'service_requests',
            filter: `user_id=eq.${userId}`
        }, callback)
        .subscribe();
}

// Export for use in HTML files
window.autoV = {
    supabase,
    getCurrentUser,
    requireAuth,
    logout,
    createServiceRequest,
    getServiceRequests,
    getServiceRequest,
    subscribeToUpdates,
    currentUser: () => currentUser,
    isAuthenticated: () => isAuthenticated
};
