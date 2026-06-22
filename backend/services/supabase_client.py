# services/supabase_client.py

import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_supabase_client():
    return supabase


# ─── PAYMENTS ───────────────────────────────────────────
def create_payment(data):
    return supabase.table("payments").insert(data).execute().data


def get_payment_by_id(payment_id):
    res = supabase.table("payments").select("*").eq("id", payment_id).execute()
    return res.data[0] if res.data else None


def get_payment_by_checkout_id(checkout_id):
    res = supabase.table("payments").select("*").eq("checkout_request_id", checkout_id).execute()
    return res.data[0] if res.data else None


def update_payment(payment_id, data):
    return supabase.table("payments").update(data).eq("id", payment_id).execute().data
