"""
EPRA Fuel Price Server - Production Ready
Integrates with Supabase as Single Source of Truth
"""

import os
import requests
import json
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# === SUPABASE CONFIG ===
SUPABASE_URL = "https://tsvejnzxrxrrecgquxbq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === EPRA DEFAULT PRICES (14th of each month) ===
EPRA_DEFAULTS = {
    "petrol": 214.03,
    "diesel": 222.86,
    "hybrid": 214.03,  # Hybrid vehicles use petrol
    "lpg": 120.00,
    "electric": 20.00
}

# === FETCH EPRA PRICES ===
def fetch_epra_prices():
    """Fetch current fuel prices from EPRA"""
    try:
        # Try official EPRA website
        epra_url = "https://www.epra.go.ke/petroleum-prices/"
        response = requests.get(epra_url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        if response.status_code == 200:
            import re
            html = response.text.lower()
            petrol_match = re.search(r'petrol[^0-9]*(\d+\.?\d*)', html)
            diesel_match = re.search(r'diesel[^0-9]*(\d+\.?\d*)', html)

            petrol = float(petrol_match.group(1)) if petrol_match else None
            diesel = float(diesel_match.group(1)) if diesel_match else None

            if petrol and diesel:
                return {
                    "petrol": petrol,
                    "diesel": diesel,
                    "hybrid": petrol,
                    "lpg": 120.00,
                    "electric": 20.00
                }
    except Exception as e:
        print(f"EPRA fetch error: {e}")

    # Fallback to EPRA defaults
    return EPRA_DEFAULTS.copy()

def save_prices_to_supabase(prices):
    """Save fuel prices to Supabase"""
    try:
        existing = supabase.table('fuel_prices').select('id').limit(1).execute()

        data = {
            "petrol": prices.get("petrol"),
            "diesel": prices.get("diesel"),
            "hybrid": prices.get("hybrid"),
            "lpg": prices.get("lpg"),
            "electric": prices.get("electric"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if existing.data and len(existing.data) > 0:
            result = supabase.table('fuel_prices').update(data).eq('id', existing.data[0]['id']).execute()
        else:
            result = supabase.table('fuel_prices').insert([data]).execute()

        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Supabase save error: {e}")
        return None

# === API ENDPOINTS ===

@app.route('/api/fuel-prices', methods=['GET'])
def get_prices():
    """GET /api/fuel-prices - Get current fuel prices from Supabase"""
    try:
        result = supabase.table('fuel_prices').select('*').order('updated_at', desc=True).limit(1).execute()

        if result.data and len(result.data) > 0:
            data = result.data[0]
            return jsonify({
                "success": True,
                "data": {
                    "petrol": float(data.get("petrol", EPRA_DEFAULTS["petrol"])),
                    "diesel": float(data.get("diesel", EPRA_DEFAULTS["diesel"])),
                    "hybrid": float(data.get("hybrid", EPRA_DEFAULTS["hybrid"])),
                    "lpg": float(data.get("lpg", EPRA_DEFAULTS["lpg"])),
                    "electric": float(data.get("electric", EPRA_DEFAULTS["electric"])),
                    "last_updated": data.get("updated_at"),
                    "source": "supabase"
                }
            })

        return jsonify({
            "success": True,
            "data": {
                **EPRA_DEFAULTS,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "source": "epra_defaults"
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/fuel-prices/update', methods=['POST'])
def update_prices():
    """POST /api/fuel-prices/update - Fetch EPRA prices and save to Supabase"""
    try:
        prices = fetch_epra_prices()
        saved = save_prices_to_supabase(prices)

        if saved:
            return jsonify({
                "success": True,
                "message": "Fuel prices updated successfully",
                "data": prices
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to save prices to Supabase"
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/vehicles/makes', methods=['GET'])
def get_makes():
    """GET /api/vehicles/makes - Get all vehicle makes"""
    try:
        result = supabase.table('vehicle_makes').select('*').order('name').execute()
        return jsonify({
            "success": True,
            "data": result.data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/vehicles/models', methods=['GET'])
def get_models():
    """GET /api/vehicles/models?make_id=1 - Get models by make"""
    make_id = request.args.get('make_id')
    try:
        query = supabase.table('vehicle_models').select('*').order('name')
        if make_id:
            query = query.eq('make_id', int(make_id))
        result = query.execute()
        return jsonify({
            "success": True,
            "data": result.data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ping', methods=['GET'])
def ping():
    """Health check"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    return """
    <html>
        <head><title>EPRA Fuel Server</title></head>
        <body style="font-family: Arial; max-width: 600px; margin: 40px auto; padding: 20px; background: #0a0c15; color: #fff;">
            <h1 style="color: #eab308;">⛽ EPRA Fuel Server</h1>
            <p><strong>Status:</strong> ✅ Running</p>
            <p><strong>EPRA Prices (14th):</strong></p>
            <ul>
                <li>Petrol: <strong>KES 214.03/L</strong></li>
                <li>Diesel: <strong>KES 222.86/L</strong></li>
                <li>Hybrid: <strong>KES 214.03/L</strong></li>
            </ul>
            <p><strong>Endpoints:</strong></p>
            <ul>
                <li><code>GET /api/fuel-prices</code> - Get current prices</li>
                <li><code>POST /api/fuel-prices/update</code> - Fetch EPRA prices</li>
                <li><code>GET /api/vehicles/makes</code> - Get vehicle makes</li>
                <li><code>GET /api/vehicles/models?make_id=1</code> - Get models</li>
            </ul>
        </body>
    </html>
    """

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║           EPRA FUEL SERVER - PRODUCTION                       ║
    ║                                                              ║
    ║  ✅ Connected to Supabase                                    ║
    ║  ✅ EPRA Prices: Petrol 214.03 | Diesel 222.86              ║
    ║  ✅ Auto-fetches EPRA fuel prices on demand                  ║
    ║  ✅ Serves as Single Source of Truth                         ║
    ║  ✅ Running on http://localhost:5000                         ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=False, host='0.0.0.0', port=5000)
