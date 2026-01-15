from __future__ import annotations

from app.models.security_event import SecurityEvent

from datetime import datetime
from functools import wraps

from flask import request, jsonify, session, abort

from app.extensions import db
from app.models.user import User
from app.models.book import Book
from app.models.book_request import BookRequest
from app.models.admin_action import AdminAction
from app.services.admin_audit import log_admin_action

from ..auth.decorators import login_required
from . import bp


ALLOWED_ROLES = {"reader", "moderator", "admin"}
ALLOWED_REQUEST_STATUSES = {"PENDING", "ACCEPTED", "REJECTED", "CANCELLED"}


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


def _json() -> dict:
    return request.get_json(silent=True) or {}


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
    Si hay alguna solicitud ACCEPTED para el libro -> is_available=False
    Si no -> is_available=True
    """
    has_accepted = (
        db.session.query(BookRequest.id)
        .filter(BookRequest.book_id == book_id, BookRequest.status == "ACCEPTED")
        .first()
        is not None
    )
    from app.extensions import db
    book = db.session.get(Book, book_id)

    if not book:
        return
    book.is_available = not has_accepted


def _parse_iso_dt(value: str) -> datetime:
    """
    Acepta ISO 8601 con o sin Z.
    Ej: 2026-01-12T14:00:00Z / 2026-01-12T14:00:00
    """
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1]
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        abort(
            400,
            description="Invalid datetime format. Use ISO 8601, e.g. 2026-01-12T14:00:00Z",
        )


# -------------------
# USERS
# -------------------


@bp.route("/users", methods=["GET"])
@login_required
@admin_required
def admin_list_users():
    q = (request.args.get("q") or "").strip()
    role = (request.args.get("role") or "").strip()
    active = (request.args.get("active") or "").strip()
    blocked = (request.args.get("blocked") or "").strip()

    query = User.query

    if q:
        if len(q) < 2:
            abort(400, description="q must be at least 2 characters")
        like = f"%{q}%"
        query = query.filter((User.username.ilike(like)) | (User.email.ilike(like)))

    if role:
        if role not in ALLOWED_ROLES:
            abort(400, description="Invalid role")
        query = query.filter(User.role == role)

    if active:
        try:
            is_active = _parse_bool(active)
        except ValueError:
            abort(400, description="active must be true/false")
        query = query.filter(User.is_active == is_active)

    if blocked:
        try:
            is_blocked = _parse_bool(blocked)
        except ValueError:
            abort(400, description="blocked must be true/false")
        query = query.filter(User.is_blocked == is_blocked)

    users = query.order_by(User.id.desc()).limit(200).all()

    return jsonify(
        [
            {
                "id": u.id,
                "username": getattr(u, "username", None),
                "email": getattr(u, "email", None),
                "role": getattr(u, "role", None),
                "is_active": getattr(u, "is_active", True),
                "is_blocked": getattr(u, "is_blocked", False),
                "created_at": u.created_at.isoformat() if getattr(u, "created_at", None) else None,
            }
            for u in users
        ]
    )


@bp.route("/users/<int:user_id>/block", methods=["PATCH"])
@login_required
@admin_required
def admin_set_user_block(user_id: int):
    data = _json()
    if "is_blocked" not in data:
        abort(400, description="Missing is_blocked")

    try:
        is_blocked = _parse_bool(data["is_blocked"])
    except ValueError:
        abort(400, description="is_blocked must be true/false")

    from flask import abort
    from app.extensions import db

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    # solo admin puede tocar a admins
    if getattr(user, "role", None) == "admin" and _role() != "admin":
        abort(403)

    # evita auto-bloqueo
    if _uid() == user_id and is_blocked:
        abort(400, description="You cannot block yourself")

    user.is_blocked = is_blocked
    db.session.commit()

    log_admin_action(
        admin_id=_uid(),
        action=AdminAction.Actions.USER_BLOCK if is_blocked else AdminAction.Actions.USER_UNBLOCK,
        target_type="user",
        target_id=user.id,
    )

    return jsonify({"message": "Block updated", "id": user.id, "is_blocked": user.is_blocked})


@bp.route("/users/<int:user_id>/status", methods=["PATCH"])
@login_required
@admin_required
def admin_set_user_status(user_id: int):
    data = _json()
    if "is_active" not in data:
        abort(400, description="Missing is_active")

    try:
        is_active = _parse_bool(data["is_active"])
    except ValueError:
        abort(400, description="is_active must be true/false")

    from flask import abort
    from app.extensions import db

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    # solo admin puede tocar a admins
    if getattr(user, "role", None) == "admin" and _role() != "admin":
        abort(403)

    # evita auto-deactivación
    if _uid() == user_id and not is_active:
        abort(400, description="You cannot deactivate yourself")

    user.is_active = is_active
    db.session.commit()

    log_admin_action(
        admin_id=_uid(),
        action="user.activate" if is_active else "user.deactivate",
        target_type="user",
        target_id=user.id,
    )

    return jsonify({"message": "Status updated", "id": user.id, "is_active": user.is_active})


@bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@login_required
@superadmin_required
def admin_set_user_role(user_id: int):
    data = _json()
    new_role = (data.get("role") or "").strip()

    if new_role not in ALLOWED_ROLES:
        abort(400, description="Invalid role")

    from flask import abort
    from app.extensions import db

    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    # evita auto-democión
    if _uid() == user_id and new_role != "admin":
        abort(400, description="You cannot change your own role away from admin")

    old_role = getattr(user, "role", None)
    user.role = new_role
    db.session.commit()

    # si has cambiado tu propio rol (aunque lo limitas), refresca session
    if _uid() == user.id:
        session["role"] = user.role

    log_admin_action(
        admin_id=_uid(),
        action=AdminAction.Actions.USER_ROLE_CHANGE,
        target_type="user",
        target_id=user.id,
    )

    return jsonify({"message": "Role updated", "id": user.id, "old_role": old_role, "role": user.role})


# -------------------
# BOOKS
# -------------------


@bp.route("/books", methods=["GET"])
@login_required
@admin_required
def admin_list_books():
    q = (request.args.get("q") or "").strip()
    available = (request.args.get("available") or "").strip()
    owner_id = (request.args.get("owner_id") or "").strip()

    query = Book.query

    if q:
        like = f"%{q}%"
        query = query.filter((Book.title.ilike(like)) | (Book.author.ilike(like)))

    if available:
        try:
            is_avail = _parse_bool(available)
        except ValueError:
            abort(400, description="available must be true/false")
        query = query.filter(Book.is_available == is_avail)

    if owner_id:
        try:
            oid = int(owner_id)
        except ValueError:
            abort(400, description="owner_id must be int")
        # tu modelo usa donor_id (según migraciones), pero respetamos si tienes user_id
        if hasattr(Book, "donor_id"):
            query = query.filter(Book.donor_id == oid)
        elif hasattr(Book, "user_id"):
            query = query.filter(Book.user_id == oid)

    books = query.order_by(Book.id.desc()).limit(200).all()

    return jsonify(
        [
            {
                "id": b.id,
                "title": b.title,
                "author": getattr(b, "author", None),
                "genre": getattr(b, "genre", None),
                "language": getattr(b, "language", None),
                "owner_id": getattr(b, "donor_id", None)
                if hasattr(b, "donor_id")
                else getattr(b, "user_id", None),
                "is_available": getattr(b, "is_available", True),
                "created_at": b.created_at.isoformat() if getattr(b, "created_at", None) else None,
            }
            for b in books
        ]
    )


@bp.route("/books/<int:book_id>/availability", methods=["PATCH"])
@login_required
@admin_required
def admin_set_book_availability(book_id: int):
    data = _json()
    if "is_available" not in data:
        abort(400, description="Missing is_available")

    try:
        is_available = _parse_bool(data["is_available"])
    except ValueError:
        abort(400, description="is_available must be true/false")

    from flask import abort
    from app.extensions import db

    book = db.session.get(Book, book_id)
    if book is None:
        abort(404)

    book.is_available = is_available
    db.session.commit()

    log_admin_action(
        admin_id=_uid(),
        action="book.set_availability",
        target_type="book",
        target_id=book.id,
    )

    return jsonify({"message": "Availability updated", "id": book.id, "is_available": book.is_available})


# -------------------
# BOOK REQUESTS
# -------------------


@bp.route("/book-requests", methods=["GET"])
@login_required
@admin_required
def admin_list_book_requests():
    status = (request.args.get("status") or "").strip()
    book_id = (request.args.get("book_id") or "").strip()
    requester_id = (request.args.get("requester_id") or "").strip()

    query = BookRequest.query

    if status:
        if status not in ALLOWED_REQUEST_STATUSES:
            abort(400, description="Invalid status")
        query = query.filter(BookRequest.status == status)

    if book_id:
        try:
            bid = int(book_id)
        except ValueError:
            abort(400, description="book_id must be int")
        query = query.filter(BookRequest.book_id == bid)

    if requester_id:
        try:
            rid = int(requester_id)
        except ValueError:
            abort(400, description="requester_id must be int")
        query = query.filter(BookRequest.requester_id == rid)

    reqs = query.order_by(BookRequest.id.desc()).limit(300).all()

    return jsonify(
        [
            {
                "id": r.id,
                "book_id": r.book_id,
                "requester_id": r.requester_id,
                "status": r.status,
                "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None,
                "updated_at": r.updated_at.isoformat() if getattr(r, "updated_at", None) else None,
            }
            for r in reqs
        ]
    )


@bp.route("/book-requests/<int:request_id>/status", methods=["PATCH"])
@login_required
@admin_required
def admin_set_request_status(request_id: int):
    data = _json()
    new_status = (data.get("status") or "").strip()

    if new_status not in ALLOWED_REQUEST_STATUSES:
        abort(400, description="Invalid status")

    from flask import abort
    from app.extensions import db

    req = db.session.get(BookRequest, request_id)
    if req is None:
        abort(404)

    # moderador limitado: solo puede REJECTED
    if _role() == "moderator" and new_status != "REJECTED":
        abort(403)

    req.status = new_status

    # sincroniza disponibilidad del libro si toca
    if new_status == "ACCEPTED":
        book = db.session.get(Book, req.book_id)
        if book is None:
            abort(404)
        book.is_available = False

    else:
        _set_book_availability_from_requests(req.book_id)

    db.session.commit()

    log_admin_action(
        admin_id=_uid(),
        action=f"request.status.{new_status.lower()}",
        target_type="request",
        target_id=req.id,
    )

    return jsonify({"message": "Request updated", "id": req.id, "status": req.status})


# -------------------
# AUDIT
# -------------------


@bp.route("/audit", methods=["GET"])
@login_required
@admin_required
def admin_list_audit():
    page = (request.args.get("page") or "1").strip()
    per_page = (request.args.get("per_page") or "50").strip()

    admin_id = (request.args.get("admin_id") or "").strip()
    action = (request.args.get("action") or "").strip()
    target_type = (request.args.get("target_type") or "").strip()
    target_id = (request.args.get("target_id") or "").strip()

    dt_from = (request.args.get("from") or "").strip()
    dt_to = (request.args.get("to") or "").strip()

    try:
        page_n = max(1, int(page))
    except ValueError:
        abort(400, description="page must be int")

    try:
        per_page_n = max(1, min(int(per_page), 200))
    except ValueError:
        abort(400, description="per_page must be int")

    q = AdminAction.query

    if admin_id:
        try:
            q = q.filter(AdminAction.admin_id == int(admin_id))
        except ValueError:
            abort(400, description="admin_id must be int")

    if action:
        q = q.filter(AdminAction.action == action)

    if target_type:
        q = q.filter(AdminAction.target_type == target_type)

    if target_id:
        try:
            q = q.filter(AdminAction.target_id == int(target_id))
        except ValueError:
            abort(400, description="target_id must be int")

    if dt_from:
        q = q.filter(AdminAction.created_at >= _parse_iso_dt(dt_from))

    if dt_to:
        q = q.filter(AdminAction.created_at <= _parse_iso_dt(dt_to))

    total = q.count()
    pages = (total + per_page_n - 1) // per_page_n

    items = (
        q.order_by(AdminAction.id.desc())
        .offset((page_n - 1) * per_page_n)
        .limit(per_page_n)
        .all()
    )

    return jsonify(
        {
            "items": [a.to_dict() for a in items],
            "page": page_n,
            "per_page": per_page_n,
            "total": total,
            "pages": pages,
        }
    )

# -------------------
# SECURITY EVENTS
# -------------------

@bp.route("/security-events", methods=["GET"])
@login_required
@admin_required
def admin_list_security_events():
    """
    Lista últimos eventos de seguridad (máx 200), con filtros básicos.
    """
    limit = (request.args.get("limit") or "100").strip()
    event_type = (request.args.get("event_type") or "").strip()
    status_code = (request.args.get("status_code") or "").strip()
    user_id = (request.args.get("user_id") or "").strip()
    ip = (request.args.get("ip") or "").strip()
    endpoint = (request.args.get("endpoint") or "").strip()
    blueprint = (request.args.get("blueprint") or "").strip()

    dt_from = (request.args.get("from") or "").strip()
    dt_to = (request.args.get("to") or "").strip()

    try:
        limit_n = max(1, min(int(limit), 200))
    except ValueError:
        abort(400, description="limit must be int")

    q = SecurityEvent.query

    if event_type:
        q = q.filter(SecurityEvent.event_type == event_type)

    if status_code:
        try:
            q = q.filter(SecurityEvent.status_code == int(status_code))
        except ValueError:
            abort(400, description="status_code must be int")

    if user_id:
        try:
            q = q.filter(SecurityEvent.user_id == int(user_id))
        except ValueError:
            abort(400, description="user_id must be int")

    if ip:
        q = q.filter(SecurityEvent.ip == ip)

    if endpoint:
        q = q.filter(SecurityEvent.endpoint == endpoint)

    if blueprint:
        q = q.filter(SecurityEvent.blueprint == blueprint)

    if dt_from:
        q = q.filter(SecurityEvent.created_at >= _parse_iso_dt(dt_from))

    if dt_to:
        q = q.filter(SecurityEvent.created_at <= _parse_iso_dt(dt_to))

    items = q.order_by(SecurityEvent.id.desc()).limit(limit_n).all()

    return jsonify(
        [
            {
                "id": e.id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "event_type": e.event_type,
                "status_code": e.status_code,
                "endpoint": e.endpoint,
                "blueprint": e.blueprint,
                "method": e.method,
                "path": e.path,
                "user_id": e.user_id,
                "role": e.role,
                "ip": e.ip,
                "details": e.details,
            }
            for e in items
        ]
    )
