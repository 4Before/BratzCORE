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
    Ensure the current user has ADMIN or ALL privilege.
    Requires `token_required` to have run before to set `g.current_user`.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = getattr(g, "current_user", None)
        if not user:
            return jsonify({"status": "error", "message": "Authentication required"}), 401

        # Verifica se o usuário tem o privilégio "ADMIN" ou "ALL"
        has_admin_privilege = user.privileges.get("ADMIN", False)
        has_all_privilege = user.privileges.get("ALL", False)
        
        if not isinstance(user.privileges, dict) or not (has_admin_privilege or has_all_privilege):
            return jsonify({"status": "error", "message": "Admin privileges required"}), 403

        return f(*args, **kwargs)
    return decorated


def privilege_required(privilege_key: str):
    """
    A decorator to ensure the current user has a specific privilege.
    
    This decorator requires `token_required` to have run before it, as it relies on `g.current_user`.
    It checks for the specific `privilege_key` and also grants access if the user has the "ALL" privilege.

    Args:
        privilege_key (str): The specific privilege string to check for.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user:
                return jsonify({"status": "error", "message": "Authentication required"}), 401
            
            # Check for the specific privilege or the "ALL" privilege
            has_specific_privilege = user.privileges.get(privilege_key, False)
            has_all_privilege = user.privileges.get("ALL", False)

            if not isinstance(user.privileges, dict) or not (has_specific_privilege or has_all_privilege):
                return jsonify({"status": "error", "message": f"Missing required privilege: '{privilege_key}'"}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


__all__ = ["token_required", "admin_required", "privilege_required"]