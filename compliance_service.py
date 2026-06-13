from risk_scoring import RiskScoringAI
from ai_result_writer import AIResultWriter

class ComplianceService:

    def __init__(self):
        self.ai = RiskScoringAI()
        self.writer = AIResultWriter()

    def process(self, vehicle_id, user_id, age, accidents, inspection_score):

        result = self.ai.score(age, accidents, inspection_score)

        self.writer.save_history(
            vehicle_id,
            "risk_assessment",
            f"Risk level: {result['risk_label']}"
        )

        return result
