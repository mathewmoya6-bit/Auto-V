from predictive_maintenance import PredictiveMaintenanceAI
from ai_result_writer import AIResultWriter

class MaintenanceService:

    def __init__(self):
        self.ai = PredictiveMaintenanceAI()
        self.writer = AIResultWriter()

    def process(self, vehicle_id, user_id, mileage, months, signals):

        result = self.ai.predict(mileage, months, signals)

        self.writer.save_history(
            vehicle_id,
            "maintenance",
            result["action"]
        )

        if result["maintenance_score"] > 0.6:
            self.writer.save_audit_log(
                user_id,
                "maintenance_alert",
                "vehicles",
                vehicle_id
            )

        return result
