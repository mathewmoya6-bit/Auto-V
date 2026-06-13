from supabase_client import supabase

def get_user_role(user_id):

    res = supabase.table("profiles") \
        .select("role") \
        .eq("id", user_id) \
        .single() \
        .execute()

    return res.data["role"]
