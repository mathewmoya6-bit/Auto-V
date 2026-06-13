class DamageLogic:

    DAMAGE_MAP = {
        "scratch": 0.05,
        "dent": 0.15,
        "crack": 0.25,
        "broken": 0.40,
        "wheel": 0.02,
        "car": 0.0
    }

    def calculate_damage(self, detections):

        score = 0

        breakdown = []

        for d in detections:

            label = d["label"].lower()
            confidence = d["confidence"]

            damage_value = self.DAMAGE_MAP.get(label, 0)

            impact = damage_value * confidence

            score += impact

            breakdown.append({
                "label": label,
                "impact": round(impact, 3)
            })

        score = min(score, 1.0)

        return {
            "damage_score": round(score, 3),
            "condition": self.get_condition(score),
            "breakdown": breakdown
        }

    def get_condition(self, score):

        if score < 0.1:
            return "Excellent"
        elif score < 0.3:
            return "Good"
        elif score < 0.6:
            return "Fair"
        else:
            return "Poor"
