from ai_service import AIService

class FraudDetectionAI:

    def analyze(self, vehicle_data, user_history):

        risk_score = 0

        if vehicle_data.get("chassis_number") is None:
            risk_score += 0.3

        if vehicle_data.get("registration_number") == "":
            risk_score += 0.2

        if user_history.get("previous_fraud_flags", 0) > 0:
            risk_score += 0.4

        risk_score = AIService.clamp(risk_score)

        return {
            "fraud_risk_score": risk_score,
            "risk_level": self.level(risk_score),
            "timestamp": AIService.now()
        }

    def level(self, score):
        if score < 0.2:
            return "Low"
        elif score < 0.5:
            return "Medium"
        else:
            return "High"
