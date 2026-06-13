from ultralytics import YOLO
import cv2

class DamageYOLO:

    def __init__(self):
        # You can replace with custom-trained model later
        self.model = YOLO("yolov8n.pt")

    def detect(self, image_path):

        results = self.model(image_path)

        detections = []

        for r in results:
            for box in r.boxes:

                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]
                confidence = float(box.conf[0])

                detections.append({
                    "label": label,
                    "confidence": round(confidence, 2)
                })

        return detections
