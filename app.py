from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from flask_cors import CORS
import bcrypt
import re
import os
from datetime import timedelta

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voting.db'  # Use SQLite for quick testing
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key-change-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
csrf = CSRFProtect(app)
CORS(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    candidate_id = db.Column(db.Integer, nullable=False)

# Validation functions
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, email.lower().strip()

def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain special character"
    return True, password

def validate_username(username):
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return False, "Username must be 3-20 alphanumeric characters"
    return True, username.strip()

def validate_vote_choice(choice):
    if not choice:
        return False, "Vote choice is required"
    choice_str = str(choice).strip()
    if not re.match(r'^[1-5]$', choice_str):
        return False, "Vote choice must be between 1 and 5"
    return True, int(choice_str)

# Routes
@app.route('/api/auth/register', methods=['POST'])
@csrf.exempt  # Exempt CSRF for registration
def register():
    data = request.get_json()
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Validate username
    is_valid, result = validate_username(username)
    if not is_valid:
        return jsonify({"success": False, "message": result}), 400
    
    # Validate email
    is_valid, result = validate_email(email)
    if not is_valid:
        return jsonify({"success": False, "message": result}), 400
    email = result
    
    # Validate password
    is_valid, result = validate_password(password)
    if not is_valid:
        return jsonify({"success": False, "message": result}), 400
    
    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered"}), 409
    
    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "Username already taken"}), 409
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
    
    # Create user
    new_user = User(username=username, email=email, password_hash=password_hash.decode('utf-8'))
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "User registered successfully",
        "user_id": str(new_user.id)
    }), 201

@app.route('/api/auth/login', methods=['POST'])
@csrf.exempt  # Exempt CSRF for login
def login():
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400
    
    user = User.query.filter_by(email=email.lower()).first()
    
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    
    # Create JWT token
    access_token = create_access_token(identity=user.id)
    
    # Generate CSRF token
    csrf_token = generate_csrf()
    
    return jsonify({
        "success": True,
        "message": "Login successful",
        "access_token": access_token,
        "csrf_token": csrf_token,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email
        }
    }), 200

@app.route('/api/vote', methods=['POST'])
@jwt_required()
def cast_vote():
    # CSRF token validation
    csrf_token = request.headers.get('X-CSRF-Token')
    if not csrf_token:
        return jsonify({"success": False, "message": "CSRF token missing"}), 403
    
    # Get vote choice
    data = request.get_json()
    vote_choice = data.get('vote_choice')
    
    # Validate vote choice
    is_valid, result = validate_vote_choice(vote_choice)
    if not is_valid:
        return jsonify({"success": False, "message": result}), 400
    
    validated_choice = result
    current_user_id = get_jwt_identity()
    
    # Check if user already voted
    existing_vote = Vote.query.filter_by(user_id=current_user_id).first()
    if existing_vote:
        return jsonify({"success": False, "message": "You have already voted"}), 409
    
    # Record vote
    new_vote = Vote(user_id=current_user_id, candidate_id=validated_choice)
    db.session.add(new_vote)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Vote recorded successfully"
    }), 201

@app.route('/api/results', methods=['GET'])
@jwt_required()
def get_results():
    results = db.session.query(
        Vote.candidate_id,
        db.func.count(Vote.id).label('count')
    ).group_by(Vote.candidate_id).all()
    
    return jsonify({
        "success": True,
        "results": [{"candidate_id": r.candidate_id, "votes": r.count} for r in results]
    }), 200

# Error handlers
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return jsonify({"success": False, "message": "CSRF token invalid"}), 403

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
