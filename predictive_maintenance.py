from ai_service import AIService

class PredictiveMaintenanceAI:

    def predict(self, mileage, last_service_months, warning_signals):

        wear = (mileage / 200000) * 0.5
        time_decay = last_service_months * 0.03
        signal_risk = len(warning_signals) * 0.1

        maintenance_score = wear + time_decay + signal_risk

        maintenance_score = AIService.clamp(maintenance_score)

        return {
            "maintenance_score": maintenance_score,
            "action": self.recommend(maintenance_score),
            "timestamp": AIService.now()
        }

    def recommend(self, score):
        if score < 0.3:
            return "No immediate maintenance required"
        elif score < 0.6:
            return "Schedule service soon"
        else:
            return "Urgent maintenance required"
