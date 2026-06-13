from supabase_client import supabase

class AdminService:

    def get_all_vehicles(self):
        return supabase.table("vehicles").select("*").execute()

    def get_all_inspections(self):
        return supabase.table("inspections").select("*").execute()

    def get_all_valuations(self):
        return supabase.table("valuations").select("*").execute()

    def get_all_payments(self):
        return supabase.table("payments").select("*").execute()
