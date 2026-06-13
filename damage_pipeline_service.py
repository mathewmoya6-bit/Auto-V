from damage_yolo import DamageYOLO
from damage_logic import DamageLogic
from ai_result_writer import AIResultWriter

class DamagePipelineService:

    def __init__(self):
        self.yolo = DamageYOLO()
        self.logic = DamageLogic()
        self.writer = AIResultWriter()

    def process(self, vehicle_id, user_id, image_path):

        # 1. Detect objects
        detections = self.yolo.detect(image_path)

        # 2. Compute damage score
        result = self.logic.calculate_damage(detections)

        # 3. Save inspection in Supabase
        self.writer.save_inspection(
            vehicle_id,
            user_id,
            result
        )

        # 4. Save vehicle history
        self.writer.save_history(
            vehicle_id,
            "ai_damage_scan",
            f"Damage: {result['condition']} (score {result['damage_score']})"
        )

        # 5. Audit log
        self.writer.save_audit_log(
            user_id,
            "damage_ai_scan",
            "inspections",
            vehicle_id
        )

        return {
            "detections": detections,
            "result": result
        }
