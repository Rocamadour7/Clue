from flask import Blueprint, current_app, jsonify, request, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime
from functools import wraps
from models import User, RefreshToken, db

user_routes_bp = Blueprint('user_routes', __name__)

def generate_token(user, token_type='access'):
    """
    Generates a JWT token for the given user.
    """
    now = datetime.utcnow()
    expires_delta = current_app.config['JWT_ACCESS_TOKEN_EXPIRES'] if token_type == 'access' else current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    payload = {
        'exp': now + expires_delta,
        'iat': now,
        'sub': user.id,
        'type': token_type
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """
    Verifies the JWT token and returns the payload if valid.
    Raises an exception if the token is invalid or expired.
    """
    try:
        print(token)
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')

def token_required(f):
    """
    Decorator to protect routes that require a valid JWT token.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Authorization token is required'}), 401
        try:
            token_type = None
            if "Bearer " in token:
                token = token.split("Bearer ")[1]
                payload = verify_token(token)
                token_type = payload['type']
            else:
                payload = verify_token(token)
            if token_type != 'access':
                return jsonify({'message': 'Invalid token type.  Expected access token.'}), 401

            user_id = payload['sub']
            user = User.query.get(user_id)
            if not user:
                return jsonify({'message': 'User not found'}), 404
            g.current_user = user
        except Exception as e:
            return jsonify({'message': str(e)}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to protect routes that only admins can access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Authorization token is required'}), 401
        try:
            payload = verify_token(token)
            user_id = payload['sub']
            user = User.query.get(user_id)
            if not user:
                return jsonify({'message': 'User not found'}), 404
            if not hasattr(user, 'is_admin') or not user.is_admin:
                return jsonify({'message': 'Admin access required'}), 403
            g.current_user = user
        except Exception as e:
            return jsonify({'message': str(e)}), 401
        return f(*args, **kwargs)
    return decorated_function

@user_routes_bp.route('/register', methods=['POST'])
def register():
    """
    Registers a new user.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        return jsonify({'message': 'Username, password, and email are required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 400

    hashed_password = generate_password_hash(password, method='sha256')
    new_user = User(username=username, password=hashed_password, email=email)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@user_routes_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticates a user and returns a JWT token.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid username or password'}), 401

    access_token = generate_token(user, 'access')
    refresh_token = generate_token(user, 'refresh')
    refresh_token_record = RefreshToken(token=refresh_token, user=user, expires_at=datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES'])
    db.session.add(refresh_token_record)
    db.session.commit()

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'message': 'Logged in successfully'
    }), 200

@user_routes_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Refreshes an expired access token using a valid refresh token.
    """
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    if not refresh_token:
        return jsonify({'message': 'Refresh token is required'}), 400

    try:
        payload = verify_token(refresh_token)
        user_id = payload['sub']
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        refresh_token_record = RefreshToken.query.filter_by(
            token=refresh_token, user_id=user_id).first()
        if not refresh_token_record or refresh_token_record.expires_at < datetime.utcnow():
            return jsonify({'message': 'Invalid or expired refresh token'}), 401

        access_token = generate_token(user, 'access')

        refresh_token_record.expires_at = datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        db.session.commit()
        return jsonify({'access_token': access_token, 'refresh_token': refresh_token}), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 401
