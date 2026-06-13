import pytesseract
import cv2

class PlateOCR:

    def read_plate(self, image_path):

        img = cv2.imread(image_path)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        text = pytesseract.image_to_string(gray)

        plate = self.clean_plate(text)

        return {
            "raw": text,
            "plate_number": plate
        }

    def clean_plate(self, text):

        import re
        plates = re.findall(r"[A-Z]{2,3}\s?\d{3}[A-Z]", text)

        return plates[0] if plates else None
