from valuation_ai import ValuationAI
from ai_result_writer import AIResultWriter

class ValuationService:

    def __init__(self):
        self.ai = ValuationAI()
        self.writer = AIResultWriter()

    def process(self, vehicle_id, user_id, base_price, year, condition_score):

        result = self.ai.estimate_value(
            base_price,
            year,
            condition_score
        )

        self.writer.save_valuation(vehicle_id, user_id, result)

        self.writer.save_history(
            vehicle_id,
            "valuation",
            f"Vehicle valued at {result['estimated_value']}"
        )

        return result
