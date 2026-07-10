# app/core/supabase_client.py
# =============================================================================
# AUTO-V API - Supabase Client
# =============================================================================
"""
Single shared Supabase client instances.

- `supabase_anon`: uses the anon key, respects Row Level Security (RLS).
  Use this for auth operations (sign in/up/out) so Supabase's own
  auth rules apply exactly as they would from a client app.

- `supabase_admin`: uses the service role key, bypasses RLS.
  Use this ONLY for trusted server-side operations (writes, admin
  lookups). Never expose this client or its key to the frontend.
"""
from supabase import create_client, Client
from app.core.config import settings

supabase_anon: Client = create_client(
    settings.supabase_url,
    settings.supabase_anon_key,
)

supabase_admin: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key,
)
