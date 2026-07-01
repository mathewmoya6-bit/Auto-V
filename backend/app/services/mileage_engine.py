"""
AUTO-V Mileage Rate Calculator — Backend API

Serves vehicle running-cost data (Kenya Vehicle Running Costs Report, Jan 2024)
and computes trip cost estimates based on category, variant and distance.

Run:
    pip install flask flask-cors
    python app.py
Then open http://localhost:5000
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os

# ─── DATA ──────────────────────────────────────────────────────────

VEHICLE_GROUPS = {
    "saloon_petrol_small": {
        "label": "Petrol Saloon — Small Engine (up to 1350cc)",
        "fuel": "Petrol",
        "variants": {
            "Up to 850cc": {"fixed_per_km": 14.79, "operating_per_km": 14.37, "total_per_km": 29.16,
                            "initial_cost": 985500},
            "851-1050cc": {"fixed_per_km": 17.29, "operating_per_km": 16.44, "total_per_km": 33.73,
                           "initial_cost": 1200000},
            "1051-1250cc": {"fixed_per_km": 22.17, "operating_per_km": 18.52, "total_per_km": 40.68,
                            "initial_cost": 1620000},
            "1251-1350cc": {"fixed_per_km": 35.89, "operating_per_km": 22.40, "total_per_km": 58.28,
                            "initial_cost": 2800000},
        },
    },
    "saloon_petrol_mid": {
        "label": "Petrol Saloon — Mid Engine (1300-1850cc)",
        "fuel": "Petrol",
        "variants": {
            "1300-1500cc": {"fixed_per_km": 34.72, "operating_per_km": 23.07, "total_per_km": 57.80,
                            "initial_cost": 2700000},
            "1451-1650cc": {"fixed_per_km": 41.70, "operating_per_km": 25.48, "total_per_km": 67.18,
                            "initial_cost": 3300000},
            "1651-1850cc (A)": {"fixed_per_km": 46.93, "operating_per_km": 28.12, "total_per_km": 75.05,
                                "initial_cost": 3750000},
            "1651-1850cc (B)": {"fixed_per_km": 78.90, "operating_per_km": 36.06, "total_per_km": 114.96,
                                "initial_cost": 6500000},
        },
    },
    "saloon_petrol_large": {
        "label": "Petrol Saloon — Large Engine (1851cc and above)",
        "fuel": "Petrol",
        "variants": {
            "1851-2000cc (A)": {"fixed_per_km": 51.00, "operating_per_km": 30.68, "total_per_km": 81.68,
                                "initial_cost": 4100000},
            "1851-2000cc (B)": {"fixed_per_km": 84.71, "operating_per_km": 39.05, "total_per_km": 123.77,
                                "initial_cost": 7000000},
            "2001-2300cc (A)": {"fixed_per_km": 45.18, "operating_per_km": 31.14, "total_per_km": 76.33,
                                "initial_cost": 3950000},
            "2001-2300cc (B)": {"fixed_per_km": 89.48, "operating_per_km": 39.51, "total_per_km": 128.99,
                                "initial_cost": 5500000},
            "2301-2600cc": {"fixed_per_km": 92.61, "operating_per_km": 48.16, "total_per_km": 140.77,
                            "initial_cost": 7700000},
            "Over 2601cc": {"fixed_per_km": 131.21, "operating_per_km": 57.70, "total_per_km": 188.91,
                            "initial_cost": 11000000},
        },
    },
    "saloon_diesel": {
        "label": "Diesel Saloon",
        "fuel": "Diesel",
        "variants": {
            "1351-1450cc": {"fixed_per_km": 38.21, "operating_per_km": 24.03, "total_per_km": 62.24,
                            "initial_cost": 3000000},
            "1501-2000cc": {"fixed_per_km": 52.16, "operating_per_km": 27.91, "total_per_km": 80.07,
                            "initial_cost": 4200000},
        },
    },
    "estate_4wd_petrol": {
        "label": "4WD Estate — Petrol",
        "fuel": "Petrol",
        "variants": {
            "1001-1600cc": {"fixed_per_km": 32.40, "operating_per_km": 25.26, "total_per_km": 57.65,
                            "initial_cost": 2500000},
            "1601-2000cc": {"fixed_per_km": 61.46, "operating_per_km": 37.48, "total_per_km": 98.94,
                            "initial_cost": 5000000},
            "2001-3000cc (A)": {"fixed_per_km": 73.08, "operating_per_km": 43.27, "total_per_km": 116.35,
                                "initial_cost": 6000000},
            "2001-3000cc (B)": {"fixed_per_km": 118.42, "operating_per_km": 54.52, "total_per_km": 172.94,
                                "initial_cost": 9900000},
            "3001-4800cc (A)": {"fixed_per_km": 134.82, "operating_per_km": 58.48, "total_per_km": 193.30,
                                "initial_cost": 9200000},
            "3001-4800cc (B)": {"fixed_per_km": 260.58, "operating_per_km": 83.89, "total_per_km": 344.47,
                                "initial_cost": 18000000},
        },
    },
    "estate_4wd_diesel": {
        "label": "4WD Estate — Diesel",
        "fuel": "Diesel",
        "variants": {
            "1500-1999cc": {"fixed_per_km": 49.83, "operating_per_km": 27.33, "total_per_km": 77.17,
                            "initial_cost": 4000000},
            "2000-3000cc (A)": {"fixed_per_km": 90.52, "operating_per_km": 43.58, "total_per_km": 134.10,
                                "initial_cost": 7500000},
            "2000-3000cc (B)": {"fixed_per_km": 137.02, "operating_per_km": 47.91, "total_per_km": 184.92,
                                "initial_cost": 11500000},
            "3001-4000cc": {"fixed_per_km": 125.40, "operating_per_km": 48.25, "total_per_km": 173.65,
                            "initial_cost": 10500000},
            "Over 4000cc (A)": {"fixed_per_km": 107.96, "operating_per_km": 61.39, "total_per_km": 169.35,
                                "initial_cost": 9000000},
            "Over 4000cc (B)": {"fixed_per_km": 177.71, "operating_per_km": 71.51, "total_per_km": 249.22,
                                "initial_cost": 15000000},
        },
    },
    "pickup_2wd_petrol": {
        "label": "2WD Pick-Up — Petrol",
        "fuel": "Petrol",
        "variants": {
            "Up to 1000cc": {"fixed_per_km": 20.77, "operating_per_km": 18.64, "total_per_km": 39.42,
                             "initial_cost": 1500000},
            "1001-1400cc": {"fixed_per_km": 26.00, "operating_per_km": 21.58, "total_per_km": 47.58,
                            "initial_cost": 1950000},
            "1401-1800cc": {"fixed_per_km": 35.88, "operating_per_km": 26.93, "total_per_km": 62.81,
                            "initial_cost": 2800000},
            "1801-2000cc": {"fixed_per_km": 37.05, "operating_per_km": 29.12, "total_per_km": 66.17,
                            "initial_cost": 2900000},
            "2001-3000cc": {"fixed_per_km": 33.56, "operating_per_km": 30.55, "total_per_km": 64.11,
                            "initial_cost": 2600000},
        },
    },
    "pickup_2wd_diesel": {
        "label": "2WD Pick-Up — Diesel",
        "fuel": "Diesel",
        "variants": {
            "1500-2000cc": {"fixed_per_km": 34.72, "operating_per_km": 25.73, "total_per_km": 60.44,
                            "initial_cost": 2700000},
        },
    },
    "pickup_4wd_diesel": {
        "label": "4WD Pick-Up — Diesel",
        "fuel": "Diesel",
        "variants": {
            "2000-3000cc": {"fixed_per_km": 44.02, "operating_per_km": 38.31, "total_per_km": 82.33,
                            "initial_cost": 3500000},
            "Over 3000cc": {"fixed_per_km": 48.67, "operating_per_km": 41.62, "total_per_km": 90.30,
                            "initial_cost": 3900000},
        },
    },
    "dcab_4wd": {
        "label": "4WD DCAB (Double Cab)",
        "fuel": "Petrol/Diesel",
        "variants": {
            "Petrol 2000-3000cc": {"fixed_per_km": 45.18, "operating_per_km": 34.81, "total_per_km": 79.99,
                                   "initial_cost": 3600000},
            "Diesel 2000-3000cc": {"fixed_per_km": 45.18, "operating_per_km": 34.79, "total_per_km": 79.96,
                                   "initial_cost": 3600000},
            "Diesel Over 3000cc": {"fixed_per_km": 59.13, "operating_per_km": 41.96, "total_per_km": 101.10,
                                   "initial_cost": 4800000},
        },
    },
    "commercial_diesel": {
        "label": "Commercial — Trucks & Mini-Bus (Diesel)",
        "fuel": "Diesel",
        "variants": {
            "3 Ton Truck": {"fixed_per_km": 51.00, "operating_per_km": 37.59, "total_per_km": 88.59,
                            "initial_cost": 4100000},
            "5 Ton Truck": {"fixed_per_km": 59.13, "operating_per_km": 40.19, "total_per_km": 99.33,
                            "initial_cost": 4800000},
            "7 Ton Truck": {"fixed_per_km": 78.90, "operating_per_km": 40.55, "total_per_km": 119.45,
                            "initial_cost": 6500000},
            "9 Ton Truck": {"fixed_per_km": 78.90, "operating_per_km": 50.78, "total_per_km": 129.68,
                            "initial_cost": 6500000},
            "Mini-Bus (2000-3000cc)": {"fixed_per_km": 59.13, "operating_per_km": 48.78, "total_per_km": 107.91,
                                       "initial_cost": 4800000},
        },
    },
}

ROAD_DISTANCES = [
    {"from": "Bungoma", "to": "Eldoret", "km": 100},
    {"from": "Eldoret", "to": "Kisumu", "km": 146},
    {"from": "Eldoret", "to": "Nakuru", "km": 253},
    {"from": "Nairobi", "to": "Nakuru", "km": 253},
    {"from": "Nairobi", "to": "Mombasa", "km": 970},
    {"from": "Kisumu", "to": "Nairobi", "km": 488},
    {"from": "Garissa", "to": "Hola", "km": 206},
    {"from": "Isiolo", "to": "Meru", "km": 134},
    {"from": "Kitale", "to": "Eldoret", "km": 143},
    {"from": "Mombasa", "to": "Nairobi", "km": 970},
    {"from": "Kisumu", "to": "Kitale", "km": 158},
    {"from": "Nairobi", "to": "Garissa", "km": 206},
]

REPORT_META = {
    "title": "Kenya Vehicle Running Costs Report",
    "period": "January 2024",
    "lowest": {"label": "Petrol Saloon up to 850cc", "rate": 29.16},
    "highest": {"label": "4WD Petrol (B) 3001-4800cc", "rate": 344.47},
}

# ─── FLASK APP ────────────────────────────────────────────────────

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)


# ─── STATIC FRONTEND ─────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ─── API ROUTES ──────────────────────────────────────────────────

@app.route("/api/meta")
def get_meta():
    """Get report metadata including period and min/max rates."""
    return jsonify(REPORT_META)


@app.route("/api/categories")
def get_categories():
    """Return all vehicle groups and their variants."""
    return jsonify(VEHICLE_GROUPS)


@app.route("/api/distances")
def get_distances():
    """Return road distances from the report appendix."""
    return jsonify(ROAD_DISTANCES)


@app.route("/api/calculate", methods=["POST"])
def calculate():
    """
    Calculate trip cost for a specific vehicle variant and distance.

    Request body: { "category": str, "variant": str, "distance_km": number }
    Response: fixed/operating/total costs per km and for the trip.
    """
    payload = request.get_json(silent=True) or {}
    category = payload.get("category")
    variant = payload.get("variant")
    distance_km = payload.get("distance_km")

    # Validate category
    if category not in VEHICLE_GROUPS:
        return jsonify({"error": f"Unknown category '{category}'"}), 400

    group = VEHICLE_GROUPS[category]

    # Validate variant
    if variant not in group["variants"]:
        return jsonify({"error": f"Unknown variant '{variant}' for category '{category}'"}), 400

    # Validate distance
    try:
        distance_km = float(distance_km)
        if distance_km < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "distance_km must be a non-negative number"}), 400

    rates = group["variants"][variant]

    # Calculate results
    result = {
        "category": category,
        "category_label": group["label"],
        "variant": variant,
        "fuel": group["fuel"],
        "distance_km": distance_km,
        "fixed_per_km": rates["fixed_per_km"],
        "operating_per_km": rates["operating_per_km"],
        "total_per_km": rates["total_per_km"],
        "initial_cost": rates["initial_cost"],
        "fixed_cost_trip": round(rates["fixed_per_km"] * distance_km, 2),
        "operating_cost_trip": round(rates["operating_per_km"] * distance_km, 2),
        "total_cost_trip": round(rates["total_per_km"] * distance_km, 2),
    }

    return jsonify(result)


# ─── RUN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚗 AUTO-V Mileage Rate Calculator")
    print(f"📂 Serving frontend from: {FRONTEND_DIR}")
    print("🌐 Open http://localhost:5000")
    app.run(debug=True, port=5000)
