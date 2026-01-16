from __future__ import annotations

from functools import wraps

from flask import request, jsonify, session, abort

from app.extensions import db

from app.models.book import Book
from app.models.book_request import BookRequest

from app.services.admin_audit import log_admin_action

from ..auth.decorators import login_required
from . import bp

from app.security.permissions import (
    role_has_permission,
    P_REQUESTS_REJECT,
    P_REQUESTS_ACCEPT,
)

ALLOWED_ROLES = {"reader", "moderator", "admin"}
ALLOWED_REQUEST_STATUSES = {"pending", "accepted", "rejected", "cancelled"}


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _uid() -> int:
    uid = session.get("user_id")
    if not uid:
        abort(401, description="auth_required")
    return int(uid)


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


def superadmin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if _role() != "admin":
            abort(403, description="superadmin_required")
        return fn(*args, **kwargs)

    return wrapper


def _parse_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        vv = v.lower().strip()
        if vv in {"true", "1", "yes"}:
            return True
        if vv in {"false", "0", "no"}:
            return False
    raise ValueError("invalid boolean")


def _set_book_availability_from_requests(book_id: int) -> None:
    """
    Si hay alguna solicitud accepted para el libro -> is_available=False
    Si no -> is_available=True
    """
    has_accepted = (
        db.session.query(BookRequest.id)
        .filter(BookRequest.book_id == book_id, BookRequest.status == "accepted")
        .first()
        is not None
    )

    book = db.session.get(Book, book_id)
    if not book:
        return

    book.is_available = not has_accepted


def _required_permission_for_request_status(new_status: str) -> str:
    s = (new_status or "").strip().lower()
    if s == "rejected":
        return P_REQUESTS_REJECT
    if s == "accepted":
        return P_REQUESTS_ACCEPT
    abort(400, description="Unsupported status transition")


@bp.route("/book-requests/<int:request_id>/status", methods=["PATCH"])
@login_required
@admin_required
def admin_set_request_status(request_id: int):
    data = _json()
    new_status = (data.get("status") or "").strip().lower()

    if new_status not in ALLOWED_REQUEST_STATUSES:
        abort(400, description="Invalid status")

    req = db.session.get(BookRequest, request_id)
    if req is None:
        abort(404)

    # ✅ v1.5: permiso por acción (no por rol)
    required_perm = _required_permission_for_request_status(new_status)
    if not role_has_permission(_role(), required_perm):
        abort(403)

    old_status = req.status
    req.status = new_status

    # sincroniza disponibilidad del libro si toca
    if new_status == "accepted":
        book = db.session.get(Book, req.book_id)
        if book is None:
            abort(404)
        book.is_available = False
    else:
        _set_book_availability_from_requests(req.book_id)

    db.session.commit()

    log_admin_action(
        admin_id=_uid(),
        action=f"request.status.{new_status}",
        target_type="request",
        target_id=req.id,
        details={"old_status": old_status, "new_status": req.status},
    )

    return jsonify({"message": "Request updated", "id": req.id, "status": req.status}), 200
