from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user_metadata = data.get('user_metadata', {})

    supabase = get_supabase()
    try:
        response = supabase.auth.sign_up({
            'email': email,
            'password': password,
            'options': {'data': user_metadata}
        })
        return jsonify({'user': response.user}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    supabase = get_supabase()
    try:
        response = supabase.auth.sign_in_with_password({'email': email, 'password': password})
        return jsonify({'user': response.user, 'session': response.session}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'Logged out'}), 200
