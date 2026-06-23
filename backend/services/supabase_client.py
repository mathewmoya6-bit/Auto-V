from db.supabase_client import force_supabase_connection, check_supabase_health

def create_app():
    # ... app setup ...
    
    # ─── FORCE SUPABASE CONNECTION ON STARTUP ────────────────
    try:
        if force_supabase_connection():
            logger.info("✅ Supabase ready")
        else:
            logger.warning("⚠️ Supabase startup check failed - will retry on first request")
    except Exception as e:
        logger.error(f"❌ Supabase init error: {e}")
    
    # ─── HEALTH CHECK ──────────────────────────────────────────
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "success": True,
            "data": {
                "status": "healthy",
                "supabase": check_supabase_health()
            }
        }), 200
