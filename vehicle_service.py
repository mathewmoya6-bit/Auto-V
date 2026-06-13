from ocr_pipeline_service import OCRPipelineService

class VehicleService:

    def __init__(self):
        self.ocr = OCRPipelineService()

    def upload_logbook(self, vehicle_id, user_id, image_path):

        return self.ocr.process_logbook(
            vehicle_id,
            user_id,
            image_path
        )
