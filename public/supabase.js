// supabase.js - Single Source of Truth
const SUPABASE_URL = "https://tsvejnzxrxrrecgquxbq.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ";

// NEW: Render Backend URL
const RENDER_API_URL = "https://auto-v.onrender.com";

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Global configuration
window.AUTO_V_CONFIG = {
    supabase: supabase,
    SUPABASE_URL: SUPABASE_URL,
    SUPABASE_ANON_KEY: SUPABASE_ANON_KEY,
    RENDER_API_URL: RENDER_API_URL,
    MPESA_SHORTCODE: "4095377",
    MPESA_CALLBACK_URL: `${RENDER_API_URL}/api/mpesa/callback`
};

console.log('✅ AUTO-V System Ready | Supabase SSOT | Render Backend');
