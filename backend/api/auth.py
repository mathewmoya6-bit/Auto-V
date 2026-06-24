# ============================================================
# api/auth.py - Authentication Routes
# ============================================================

import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")

        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400

        # Check if user exists
        existing = (
            supabase.table("user_profiles")
            .select("*")
            .eq("email", email)
            .execute()
        )

        if existing.data:
            return jsonify({"success": False, "error": "User already exists"}), 400

        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        if not auth_response.user:
            return jsonify({"success": False, "error": "Registration failed"}), 400

        # Create user profile
        profile_data = {
            "id": auth_response.user.id,
            "email": email,
            "full_name": full_name,
            "created_at": datetime.utcnow().isoformat()
        }

        supabase.table("user_profiles").insert(profile_data).execute()

        return jsonify({
            "success": True,
            "data": {
                "user_id": auth_response.user.id,
                "email": email,
                "message": "User registered successfully"
            }
        }), 201

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login a user."""
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400

        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not auth_response.user:
            return jsonify({"success": False, "error": "Invalid credentials"}), 401

        return jsonify({
            "success": True,
            "data": {
                "user_id": auth_response.user.id,
                "email": auth_response.user.email,
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token
            }
        }), 200

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": str(e)}), 401


@auth_bp.route("/profile/<user_id>", methods=["GET"])
def get_profile(user_id):
    """Get user profile."""
    try:
        result = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if not result.data:
            return jsonify({"success": False, "error": "User not found"}), 404

        return jsonify({"success": True, "data": result.data[0]}), 200

    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Logout user."""
    try:
        # Supabase handles logout on client side
        return jsonify({"success": True, "message": "Logged out successfully"}), 200

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
