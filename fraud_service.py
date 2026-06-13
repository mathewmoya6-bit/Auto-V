from fraud_detection import FraudDetectionAI
from ai_result_writer import AIResultWriter

class FraudService:

    def __init__(self):
        self.ai = FraudDetectionAI()
        self.writer = AIResultWriter()

    def process(self, vehicle_data, user_history, user_id):

        result = self.ai.analyze(vehicle_data, user_history)

        if result["risk_level"] == "High":

            self.writer.save_audit_log(
                user_id,
                "fraud_alert",
                "vehicles",
                vehicle_data.get("id")
            )

        return result
