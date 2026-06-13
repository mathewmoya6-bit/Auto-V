import numpy as np
from datetime import datetime

class AIService:

    @staticmethod
    def normalize(value, min_val, max_val):
        if max_val == min_val:
            return 0
        return (value - min_val) / (max_val - min_val)

    @staticmethod
    def clamp(value, min_val=0, max_val=1):
        return max(min_val, min(value, max_val))

    @staticmethod
    def now():
        return datetime.utcnow().isoformat()
