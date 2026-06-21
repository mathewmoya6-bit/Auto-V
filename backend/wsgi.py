# wsgi.py - Production WSGI Entry Point
"""
AUTO-V WSGI Application
Production entry point for Gunicorn/Waitress
"""

import os
import sys
import logging

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set up logging before importing app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the Flask app
from app import app as application

# For Gunicorn/Waitress
app = application

# Optional: Print startup info
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AUTO-V API Production Server")
    print("=" * 60)
    print(f"📦 Environment: {app.config.get('ENV', 'production')}")
    print(f"🔑 M-Pesa Shortcode: {app.config.get('MPESA_SHORTCODE', 'N/A')}")
    print(f"📋 Routes registered")
    print("=" * 60)
