from flask import Blueprint, request
from models.user import User
from utils.responses import success_response, error_response
from utils.jwt_manager import generate_token
from utils.extensions import db 

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/auth", methods=["POST"])
def auth():
    """
    Register a basic user with email and password
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    confirm = data.get("confirm_password")
    account_type = data.get("account_type", "BASIC")

    if not all([email, password, confirm]):
        return error_response("Missing fields", 400)

    if password != confirm:
        return error_response("Passwords do not match", 400)

    if User.query.filter_by(email=email).first():
        return error_response("Email already registered", 409)

    user = User(email=email, account_type=account_type, privileges={})
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    token = generate_token(user)

    return success_response("User registered", {
        "token": token,
        "email": user.email,
        "account_type": user.account_type
    }, 201)


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """
    Login with email and password
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return error_response("Invalid credentials", 401)

    token = generate_token(user)

    return success_response("Login successful", {
        "token": token,
        "email": user.email,
        "account_type": user.account_type,
        "privileges": user.privileges
    })
