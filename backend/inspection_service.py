from damage_detection import DamageDetectionAI
from ai_result_writer import AIResultWriter

class InspectionService:

    def __init__(self):
        self.ai = DamageDetectionAI()
        self.writer = AIResultWriter()

    def process(self, vehicle_id, user_id, detected_objects):

        result = self.ai.analyze(detected_objects)

        self.writer.save_inspection(vehicle_id, user_id, result)

        self.writer.save_history(
            vehicle_id,
            "inspection",
            f"Inspection completed: {result['condition']}"
        )

        return result
