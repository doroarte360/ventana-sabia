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
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = session.get("role")
            if not session.get("user_id"):
                return jsonify(error="auth_required"), 401
            if role not in roles:
                return jsonify(error="forbidden", required=list(roles), current=role), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
