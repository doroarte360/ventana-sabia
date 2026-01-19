# app/blueprints/admin_api/routes.py
from __future__ import annotations

from functools import wraps

from flask import jsonify, request, abort, session

from app.extensions import db
from app.models.user import User
from app.security.permissions import (
    role_has_permission,
    P_USERS_READ,
    P_USERS_UPDATE_BLOCK,
)
from app.blueprints.auth.decorators import login_required

from . import bp


def _role() -> str:
    role = session.get("role")
    if not role:
        abort(401, description="auth_required")
    return str(role)


def _uid() -> int:
    return int(session.get("user_id") or 0)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Permitimos entrar a admin y moderator, pero permisos finos deciden dentro
        if _role() not in {"admin", "moderator"}:
            abort(403, description="admin_required")
        return fn(*args, **kwargs)

    return wrapper


@bp.get("/users")
@login_required
@admin_required
def api_admin_list_users():
    # Permiso fino (v1.5)
    if not role_has_permission(_role(), P_USERS_READ):
        abort(403, description="forbidden")

    q = (request.args.get("q") or "").strip()
    query = User.query

    if q:
        like = f"%{q}%"
        query = query.filter((User.username.ilike(like)) | (User.email.ilike(like)))

    users = query.order_by(User.id.desc()).limit(200).all()

    return jsonify(
        [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "is_active": bool(getattr(u, "is_active", True)),
                "is_blocked": bool(getattr(u, "is_blocked", False)),
            }
            for u in users
        ]
    ), 200


@bp.patch("/users/<int:user_id>/block")
@login_required
@admin_required
def api_admin_set_user_block(user_id: int):
    # Permiso fino (v1.5)
    if not role_has_permission(_role(), P_USERS_UPDATE_BLOCK):
        abort(403, description="forbidden")

    data = request.get_json(silent=True) or {}
    if "is_blocked" not in data:
        abort(400, description="missing_is_blocked")

    v = data["is_blocked"]
    if isinstance(v, bool):
        is_blocked = v
    elif isinstance(v, str) and v.strip().lower() in {"true", "1", "yes"}:
        is_blocked = True
    elif isinstance(v, str) and v.strip().lower() in {"false", "0", "no"}:
        is_blocked = False
    else:
        abort(400, description="is_blocked_must_be_true_false")

    user = db.session.get(User, user_id)
    if user is None:
        abort(404, description="not_found")

    # solo admin puede tocar a admins
    if getattr(user, "role", None) == "admin" and _role() != "admin":
        abort(403, description="cannot_block_admin")

    # evita auto-bloqueo
    if _uid() == user_id and is_blocked:
        abort(400, description="cannot_block_yourself")

    old_blocked = bool(getattr(user, "is_blocked", False))
    user.is_blocked = is_blocked
    db.session.commit()

    return jsonify(
        {
            "message": "ok",
            "id": user.id,
            "old_is_blocked": old_blocked,
            "is_blocked": bool(user.is_blocked),
        }
    ), 200
