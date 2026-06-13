from ai_service import AIService

class RiskScoringAI:

    def score(self, vehicle_age, accident_history, inspection_score):

        age_risk = min(vehicle_age * 0.05, 0.5)
        accident_risk = min(accident_history * 0.2, 0.6)
        inspection_risk = 1 - inspection_score

        total_risk = age_risk + accident_risk + inspection_risk

        total_risk = AIService.clamp(total_risk)

        return {
            "risk_score": total_risk,
            "risk_label": self.label(total_risk),
            "timestamp": AIService.now()
        }

    def label(self, score):
        if score < 0.3:
            return "Low Risk"
        elif score < 0.6:
            return "Medium Risk"
        else:
            return "High Risk"
