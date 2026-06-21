# app.py – AUTO-V Flask Application (PRODUCTION READY)

# ... (keep everything the same until register_blueprints) ...

# ─── REGISTER BLUEPRINTS ──────────────────────────────────────
def register_blueprints():
    """Register all blueprints."""
    registered = 0
    
    # ─── M-Pesa Routes ──────────────────────────────────────────
    try:
        from api.routes.mpesa import mpesa_bp
        app.register_blueprint(mpesa_bp, url_prefix='/api/mpesa')
        registered += 1
        logger.info("✅ Registered: /api/mpesa")
    except Exception as e:
        logger.warning(f"⚠️ M-Pesa routes not available: {e}")
    
    # ─── Mileage Routes ─────────────────────────────────────────
    try:
        from api.routes.mileage import mileage_bp
        app.register_blueprint(mileage_bp, url_prefix='/api/mileage')
        registered += 1
        logger.info("✅ Registered: /api/mileage")
    except Exception as e:
        logger.warning(f"⚠️ Mileage routes not available: {e}")
    
    return registered

# ─── REMOVE DUPLICATE M-PESA ROUTES FROM app.py ──────────────
# Delete these from app.py (they're now in the blueprint):
# - @app.route('/api/mpesa/initiate', ...)
# - @app.route('/api/mpesa/status/<payment_id>', ...)
# - @app.route('/api/mpesa/auto-confirm/<payment_id>', ...)
# - @app.route('/api/mpesa/query/<checkout_id>', ...)
# - @app.route('/api/mpesa/configured', ...)
# - @app.route('/mpesa/callback', ...)  # Keep this one separate if needed

# ─── Keep ONLY the /mpesa/callback route in app.py ──────────
@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa STK Push callback."""
    # ... (keep the existing callback handler) ...

# ─── REMOVE the duplicate /api/mpesa/configured route ───────
# The blueprint now handles /api/mpesa/health and /api/mpesa/test
