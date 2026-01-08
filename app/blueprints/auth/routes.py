from flask import Blueprint, request, jsonify, session
from sqlalchemy import or_

from ...extensions import db
from ...models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


# ---------- REGISTER ----------
@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not email or not username or not password:
        return jsonify(
            error="missing_fields",
            required=["email", "username", "password"]
        ), 400

    if len(password) < 8:
        return jsonify(
            error="weak_password",
            min_length=8
        ), 400

    exists = User.query.filter(
        or_(User.email == email, User.username == username)
    ).first()

    if exists:
        return jsonify(error="user_exists"), 409

    user = User(email=email, username=username)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # ✅ recomendado: deja al usuario logueado tras registrarse
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role

    return jsonify(
        message="created",
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role
    ), 201

# ---------- LOGIN ----------
@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify(
            error="missing_fields",
            required=["email", "password"]
        ), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify(error="invalid_credentials"), 401

    if not user.is_active:
        return jsonify(error="user_blocked"), 403

    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role

    return jsonify(
        message="ok",
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role
    ), 200


# ---------- LOGOUT ----------
@bp.post("/logout")
def logout():
    session.clear()
    return jsonify(message="logged_out"), 200


# ---------- WHO AM I ----------
@bp.get("/me")
def me():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify(authenticated=False), 200

    user = User.query.get(user_id)

    if not user:
        session.clear()
        return jsonify(authenticated=False), 200

    return jsonify(
        authenticated=True,
        id=user.id,
        email=user.email,
        username=user.username,
        role=session.get("role")
    ), 200
