from ocr_service import OCRService
from ai_result_writer import AIResultWriter
from supabase_client import supabase

class OCRPipelineService:

    def __init__(self):
        self.ocr = OCRService()
        self.writer = AIResultWriter()

    def process_logbook(self, vehicle_id, user_id, image_path):

        result = self.ocr.extract_text(image_path)
        vehicle_data = self.ocr.extract_vehicle_data(result["raw_text"])

        # Update vehicle record in Supabase
        supabase.table("vehicles").update({
            **vehicle_data
        }).eq("id", vehicle_id).execute()

        # Save history event
        self.writer.save_history(
            vehicle_id,
            "ocr_logbook",
            f"Logbook scanned and updated: {vehicle_data}"
        )

        # Audit log
        self.writer.save_audit_log(
            user_id,
            "ocr_logbook_scan",
            "vehicles",
            vehicle_id
        )

        return {
            "extracted_text": result["clean_text"],
            "vehicle_data": vehicle_data
        }
