from functools import wraps
from flask import session, jsonify
from app.extensions import db
from app.models.user import User

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify(error="auth_required"), 401

        user = db.session.get(User, user_id)
        if not user:
            return jsonify(error="auth_required"), 401

        if not user.is_active:
            return jsonify(error="user_inactive"), 403

        if user.is_blocked:
            return jsonify(error="user_blocked"), 403

        return fn(*args, **kwargs)
    return wrapper
