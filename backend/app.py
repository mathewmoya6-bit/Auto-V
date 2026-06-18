import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# ─── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# ─── Rate Limiting ──────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# ─── App ────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins=['https://auto-v.meipressgroup.com', 'https://auto-v.vercel.app', 'https://auto-v.onrender.com'])  # Restrict CORS

limiter.init_app(app)

# ─── Security Headers ──────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# ─── Import Blueprints ──────────────────────────────────────
from api.auth import auth_bp
from api.payments import payments_bp
from api.valuations import valuations_bp
from api.inspections import inspections_bp
from api.intelligence import intelligence_bp
from api.webhooks import webhooks_bp
from api.mileage import mileage_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(payments_bp, url_prefix='/api/payments')
app.register_blueprint(valuations_bp, url_prefix='/api/valuations')
app.register_blueprint(inspections_bp, url_prefix='/api/inspections')
app.register_blueprint(intelligence_bp, url_prefix='/api/intelligence')
app.register_blueprint(webhooks_bp, url_prefix='/api/webhooks')
app.register_blueprint(mileage_bp, url_prefix='/api/mileage')

# ─── Health & Root ──────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/')
def root():
    return jsonify({
        'service': 'AUTO-V Backend',
        'version': '2.0.0',
        'status': 'running'
    })

# ─── Run ────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
