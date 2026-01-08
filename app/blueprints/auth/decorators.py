from functools import wraps
from flask import session, jsonify

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(error="auth_required"), 401
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    """
    Uso:
      @role_required("admin")
      @role_required("admin", "moderator")
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return jsonify(error="auth_required"), 401

            role = session.get("role")
            if role not in roles:
                return jsonify(
                    error="forbidden",
                    required_roles=list(roles),
                    current_role=role
                ), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
