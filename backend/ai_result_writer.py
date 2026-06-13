from supabase_client import supabase
from ai_service import AIService

class AIResultWriter:

    def save_valuation(self, vehicle_id, user_id, result):

        data = {
            "vehicle_id": vehicle_id,
            "user_id": user_id,
            "value": result["estimated_value"],
            "condition_score": result.get("condition_multiplier", 0),
            "ai_score": 1 - result.get("condition_multiplier", 0),
        }

        return supabase.table("valuations").insert(data).execute()


    def save_inspection(self, vehicle_id, user_id, damage_result):

        data = {
            "vehicle_id": vehicle_id,
            "user_id": user_id,
            "overall_score": 1 - damage_result["damage_score"],
            "status": damage_result["condition"],
            "notes": f"AI detected damage score {damage_result['damage_score']}"
        }

        return supabase.table("inspections").insert(data).execute()


    def save_history(self, vehicle_id, event_type, description):

        data = {
            "vehicle_id": vehicle_id,
            "event_type": event_type,
            "description": description
        }

        return supabase.table("vehicle_history").insert(data).execute()


    def save_audit_log(self, user_id, action, table_name, record_id):

        data = {
            "user_id": user_id,
            "action": action,
            "table_name": table_name,
            "record_id": str(record_id),
            "metadata": {}
        }

        return supabase.table("audit_logs").insert(data).execute()
