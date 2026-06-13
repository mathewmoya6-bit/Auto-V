from typing import List, Dict, Any
from services.supabase_client import get_supabase

class AdminService:
    def __init__(self):
        self.supabase = get_supabase()
    
    def get_all_vehicles(self) -> List[Dict]:
        result = self.supabase.table("vehicles").select("*").execute()
        return result.data
    
    def get_all_inspections(self) -> List[Dict]:
        result = self.supabase.table("inspections").select("*").execute()
        return result.data
    
    def get_all_valuations(self) -> List[Dict]:
        result = self.supabase.table("valuations").select("*").execute()
        return result.data
    
    def get_all_payments(self) -> List[Dict]:
        result = self.supabase.table("payments").select("*").execute()
        return result.data
    
    # Add pagination for large datasets
    def get_all_vehicles_paginated(self, page: int = 1, page_size: int = 50):
        start = (page - 1) * page_size
        end = start + page_size - 1
        
        result = self.supabase.table("vehicles") \
            .select("*") \
            .range(start, end) \
            .execute()
        
        return {
            "data": result.data,
            "page": page,
            "page_size": page_size
        }
