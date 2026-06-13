from ai_service import AIService

class ValuationAI:

    def estimate_value(self, base_price, year, condition_score, mileage_factor=1.0):

        age_penalty = max(0, (2026 - year) * 0.02)

        condition_multiplier = 1 - condition_score  # worse condition = lower value

        estimated_value = base_price * (1 - age_penalty) * condition_multiplier * mileage_factor

        return {
            "estimated_value": round(estimated_value, 2),
            "age_penalty": age_penalty,
            "condition_multiplier": condition_multiplier,
            "timestamp": AIService.now()
        }
