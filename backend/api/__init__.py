# api/__init__.py – AUTO-V FastAPI Application (Production-Ready)

# api/__init__.py – Flask Application
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')

CORS(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

# Health check
@app.route('/')
def root():
    return jsonify({"status": "AUTO-V API running", "framework": "Flask"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# Import and register blueprints
from api.routes.auth import auth_bp
from api.routes.valuation import valuation_bp
# ... import all blueprints

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(valuation_bp, url_prefix='/api/valuation')
# ... register all blueprints
