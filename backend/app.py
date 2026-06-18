import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from api.auth import auth_bp
from api.payments import payments_bp
from api.valuations import valuations_bp
from api.inspections import inspections_bp
from api.intelligence import intelligence_bp
from api.webhooks import webhooks_bp
from api.mileage import mileage_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(payments_bp, url_prefix='/api/payments')
app.register_blueprint(valuations_bp, url_prefix='/api/valuations')
app.register_blueprint(inspections_bp, url_prefix='/api/inspections')
app.register_blueprint(intelligence_bp, url_prefix='/api/intelligence')
app.register_blueprint(webhooks_bp, url_prefix='/api/webhooks')
app.register_blueprint(mileage_bp, url_prefix='/api/mileage')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/')
def root():
    return jsonify({
        'service': 'AUTO-V Backend',
        'version': '1.0.0',
        'status': 'running'
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
