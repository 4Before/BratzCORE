from functools import wraps
from flask import request, jsonify, g
from models.user import User
from utils.jwt_manager import decode_token

def token_required(f):
    """
    Ensure the request has a valid Bearer JWT token.
    Attaches the current user to `g.current_user`.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"status": "error", "message": "Authorization header missing or invalid"}), 401

        token = parts[1]
        payload = decode_token(token)
        if not payload:
            return jsonify({"status": "error", "message": "Invalid or expired token"}), 401

        user = User.query.get(payload.get("user_id"))
        if not user:
            return jsonify({"status": "error", "message": "User no longer exists"}), 401

        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """
    Ensure the current user has ADMIN privilege.
    Requires `token_required` to have run before to set `g.current_user`.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = getattr(g, "current_user", None)
        if not user:
            return jsonify({"status": "error", "message": "Authentication required"}), 401

        if not isinstance(user.privileges, dict) or not user.privileges.get("ADMIN", False):
            return jsonify({"status": "error", "message": "Admin privileges required"}), 403

        return f(*args, **kwargs)
    return decorated

__all__ = ["token_required", "admin_required"]
