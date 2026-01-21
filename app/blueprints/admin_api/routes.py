from __future__ import annotations

from flask import jsonify, request, abort, session
from functools import wraps

from app.extensions import db
from app.models.user import User
from app.models.book import Book
from app.models.book_request import BookRequest

from app.security.permissions import (
    role_has_permission,
    P_USERS_READ,
    P_USERS_UPDATE_BLOCK,
    P_REQUESTS_READ,
    P_REQUESTS_ACCEPT,
    P_REQUESTS_REJECT,
)

from app.blueprints.auth.decorators import login_required
from . import bp


ALLOWED_REQUEST_STATUSES = {"pending", "accepted", "rejected", "cancelled"}


def _role() -> str:
    role = session.get("role")
    if not role:
        abort(401, description="auth_required")
    return str(role)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if _role() not in {"admin", "moderator"}:
            abort(403, description="admin_required")
        return fn(*args, **kwargs)

    return wrapper


# -----------------------
# USERS (lo tuyo)
# -----------------------
@bp.get("/users")
@login_required
@admin_required
def api_admin_list_users():
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
    )


@bp.patch("/users/<int:user_id>/block")
@login_required
@admin_required
def api_admin_set_user_block(user_id: int):
    if not role_has_permission(_role(), P_USERS_UPDATE_BLOCK):
        abort(403, description="forbidden")

    data = request.get_json(silent=True) or {}
    if "is_blocked" not in data:
        abort(400, description="Missing is_blocked")

    v = data["is_blocked"]
    if isinstance(v, bool):
        is_blocked = v
    elif isinstance(v, str) and v.strip().lower() in {"true", "1", "yes"}:
        is_blocked = True
    elif isinstance(v, str) and v.strip().lower() in {"false", "0", "no"}:
        is_blocked = False
    else:
        abort(400, description="is_blocked must be true/false")

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    if getattr(user, "role", None) == "admin" and _role() != "admin":
        abort(403, description="cannot_block_admin")

    if session.get("user_id") == user_id and is_blocked:
        abort(400, description="You cannot block yourself")

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


# -----------------------
# BOOK REQUESTS (NUEVO)
# -----------------------
@bp.get("/book-requests")
@login_required
@admin_required
def api_admin_list_book_requests():
    if not role_has_permission(_role(), P_REQUESTS_READ):
        abort(403, description="forbidden")

    status = (request.args.get("status") or "").strip().lower()
    book_id = (request.args.get("book_id") or "").strip()
    requester_id = (request.args.get("requester_id") or "").strip()

    q = BookRequest.query

    if status:
        if status not in ALLOWED_REQUEST_STATUSES:
            abort(400, description="Invalid status")
        q = q.filter(BookRequest.status == status)

    if book_id:
        try:
            bid = int(book_id)
        except ValueError:
            abort(400, description="book_id must be int")
        q = q.filter(BookRequest.book_id == bid)

    if requester_id:
        try:
            rid = int(requester_id)
        except ValueError:
            abort(400, description="requester_id must be int")
        q = q.filter(BookRequest.requester_id == rid)

    items = q.order_by(BookRequest.id.desc()).limit(300).all()

    return jsonify(
        [
            {
                "id": r.id,
                "book_id": r.book_id,
                "requester_id": r.requester_id,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in items
        ]
    )


def _required_perm_for_request_status(new_status: str) -> str:
    s = (new_status or "").strip().lower()
    if s == "accepted":
        return P_REQUESTS_ACCEPT
    if s == "rejected":
        return P_REQUESTS_REJECT
    abort(400, description="Only accepted/rejected allowed here")


@bp.patch("/book-requests/<int:request_id>/status")
@login_required
@admin_required
def api_admin_set_book_request_status(request_id: int):
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip().lower()

    if new_status not in {"accepted", "rejected"}:
        abort(400, description="status must be accepted|rejected")

    required_perm = _required_perm_for_request_status(new_status)
    if not role_has_permission(_role(), required_perm):
        abort(403, description="forbidden")

    req = db.session.get(BookRequest, request_id)
    if req is None:
        abort(404)

    old_status = req.status
    req.status = new_status

    # sincroniza disponibilidad del libro
    if new_status == "accepted":
        book = db.session.get(Book, req.book_id)
        if book:
            book.is_available = False
    else:
        # si rechazamos, no cambiamos disponibilidad a true a ciegas:
        # la dejas como esté (o si quieres, implementamos recalculo)
        pass

    db.session.commit()

    return jsonify(
        {
            "message": "ok",
            "id": req.id,
            "old_status": old_status,
            "status": req.status,
        }
    ), 200
