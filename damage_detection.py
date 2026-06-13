from ai_service import AIService

class DamageDetectionAI:

    DAMAGE_WEIGHTS = {
        "scratch": 0.05,
        "dent": 0.15,
        "broken_light": 0.25,
        "cracked_glass": 0.30,
        "major_damage": 0.60
    }

    def analyze(self, detected_objects: list):
        """
        detected_objects example:
        ["scratch", "dent"]
        """

        damage_score = 0

        for obj in detected_objects:
            damage_score += self.DAMAGE_WEIGHTS.get(obj, 0)

        damage_score = AIService.clamp(damage_score, 0, 1)

        condition = self.get_condition(damage_score)

        return {
            "damage_score": damage_score,
            "condition": condition,
            "timestamp": AIService.now()
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
