import pytesseract
from PIL import Image
import re

class OCRService:

    def extract_text(self, image_path):

        image = Image.open(image_path)

        text = pytesseract.image_to_string(image)

        return {
            "raw_text": text,
            "clean_text": self.clean(text)
        }

    def clean(self, text):
        return " ".join(text.split())


    # ---------------------------
    # VEHICLE DATA EXTRACTION
    # ---------------------------
    def extract_vehicle_data(self, text):

        data = {}

        # Registration number (Kenya format example)
        reg = re.findall(r"[A-Z]{2,3}\s?\d{3}[A-Z]", text)
        if reg:
            data["registration_number"] = reg[0]

        # Chassis number (simple pattern)
        chassis = re.findall(r"[A-HJ-NPR-Z0-9]{10,}", text)
        if chassis:
            data["chassis_number"] = chassis[0]

        # Engine number (heuristic)
        engine = re.findall(r"ENG[:\s]*[A-Z0-9-]+", text, re.IGNORECASE)
        if engine:
            data["engine_number"] = engine[0].replace("ENG", "").strip()

        return data
