import logging
import sys
from datetime import datetime
from config import settings

def setup_logger():
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"logs/app_{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()
