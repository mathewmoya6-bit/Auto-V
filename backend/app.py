# app.py – AUTO-V Flask Application Entry Point

import os
import logging
from api import app

# Configure logging for the entry point
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Get port from environment variable (Render sets this)
    port = int(os.getenv('PORT', 5000))
    
    # Run the Flask app
    # debug=False is required for production
    app.run(
        host='0.0.0.0',  # Required for Render
        port=port,
        debug=False,
        threaded=True   # Handle multiple requests
    )
