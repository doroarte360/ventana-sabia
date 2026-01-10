# app/blueprints/admin/routes.py

from flask import request, jsonify, abort, session
from ..auth.decorators import login_required
from . import bp




from app.extensions import db
from app.models.user import User
from app.models.book import Book
from app.models.book_request import BookRequest

from functools import wraps

def _uid():
    uid = session.get("user_id")
    if not uid:
        abort(401)
    return uid

def _role():
    role = session.get("role")
    if not role:
        abort(401)
    return role


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if _role() not in {"admin", "moderator"}:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def superadmin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if _role() != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

# Si tu blueprint ya existe, no lo redefinas aquí.
# from . import bp

ALLOWED_ROLES = {"reader", "moderator", "admin"}
ALLOWED_REQUEST_STATUSES = {"PENDING", "ACCEPTED", "REJECTED", "CANCELLED"}




def _json():
    data = request.get_json(silent=True)
    return data or {}


def _parse_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v.lower() in {"true", "1", "yes"}:
            return True
        if v.lower() in {"false", "0", "no"}:
            return False
    raise ValueError("invalid boolean")


def _set_book_availability_from_requests(book_id: int):
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
    book = Book.query.get(book_id)
    if not book:
        return
    book.is_available = (not has_accepted)


# -------------------
# USERS
# -------------------

@bp.route("/users", methods=["GET"])
@login_required
@admin_required
def admin_list_users():
    # filtros opcionales: ?q=toni&role=reader&active=true
    q = (request.args.get("q") or "").strip()
    role = (request.args.get("role") or "").strip()
    active = (request.args.get("active") or "").strip()

    query = User.query

    if q:
        like = f"%{q}%"
        # ajusta campos si tu User no tiene email/username
        query = query.filter(
            (User.username.ilike(like)) | (User.email.ilike(like))
        )

    if role:
        query = query.filter(User.role == role)

    if active:
        try:
            is_active = _parse_bool(active)
            query = query.filter(User.is_active == is_active)
        except ValueError:
            abort(400, "active must be true/false")

    users = query.order_by(User.id.desc()).limit(200).all()

    return jsonify([
        {
            "id": u.id,
            "username": getattr(u, "username", None),
            "email": getattr(u, "email", None),
            "role": getattr(u, "role", None),
            "is_active": getattr(u, "is_active", True),
            "created_at": getattr(u, "created_at", None),
        }
        for u in users
    ])


@bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@login_required
@superadmin_required
def admin_change_user_role(user_id):
    data = _json()
    new_role = (data.get("role") or "").strip()

    if new_role not in ALLOWED_ROLES:
        abort(400, "Invalid role")

    # evita lock-out
    if _uid() == user_id and new_role != "admin":
        abort(400, "You cannot remove your own admin role")

    user = User.query.get_or_404(user_id)
    user.role = new_role
    db.session.commit()

    return jsonify({"message": "Role updated", "id": user.id, "role": user.role})


@bp.route("/users/<int:user_id>/status", methods=["PATCH"])
@login_required
@admin_required
def admin_set_user_status(user_id):
    data = _json()
    if "is_active" not in data:
        abort(400, "Missing is_active")

    try:
        is_active = _parse_bool(data["is_active"])
    except ValueError:
        abort(400, "is_active must be true/false")

    user = User.query.get_or_404(user_id)

    # regla: solo admin puede tocar a admins
    if getattr(user, "role", None) == "admin" and _role() != "admin":
        abort(403)

    # evita auto-bloqueo accidental
    if _uid() == user_id and not is_active:
        abort(400, "You cannot deactivate yourself")

    user.is_active = is_active
    db.session.commit()

    return jsonify({"message": "Status updated", "id": user.id, "is_active": user.is_active})


# -------------------
# BOOKS
# -------------------

@bp.route("/books", methods=["GET"])
@login_required
@admin_required
def admin_list_books():
    # filtros: ?available=true&owner_id=1&q=harry
    q = (request.args.get("q") or "").strip()
    available = (request.args.get("available") or "").strip()
    owner_id = (request.args.get("owner_id") or "").strip()

    query = Book.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Book.title.ilike(like)) | (Book.author.ilike(like))
        )

    if available:
        try:
            is_avail = _parse_bool(available)
            query = query.filter(Book.is_available == is_avail)
        except ValueError:
            abort(400, "available must be true/false")

    if owner_id:
        try:
            oid = int(owner_id)
        except ValueError:
            abort(400, "owner_id must be int")
        # ajusta si tu campo no es user_id
        query = query.filter(Book.user_id == oid)

    books = query.order_by(Book.id.desc()).limit(200).all()

    return jsonify([
        {
            "id": b.id,
            "title": b.title,
            "author": getattr(b, "author", None),
            "genre": getattr(b, "genre", None),
            "language": getattr(b, "language", None),
            "owner_id": getattr(b, "user_id", None),
            "is_available": getattr(b, "is_available", True),
            "created_at": getattr(b, "created_at", None),
        }
        for b in books
    ])


@bp.route("/books/<int:book_id>/availability", methods=["PATCH"])
@login_required
@admin_required
def admin_set_book_availability(book_id):
    data = _json()
    if "is_available" not in data:
        abort(400, "Missing is_available")

    try:
        is_available = _parse_bool(data["is_available"])
    except ValueError:
        abort(400, "is_available must be true/false")

    book = Book.query.get_or_404(book_id)
    book.is_available = is_available
    db.session.commit()

    return jsonify({"message": "Availability updated", "id": book.id, "is_available": book.is_available})


# -------------------
# BOOK REQUESTS
# -------------------

@bp.route("/book-requests", methods=["GET"])
@login_required
@admin_required
def admin_list_book_requests():
    # filtros: ?status=PENDING&book_id=1&requester_id=2
    status = (request.args.get("status") or "").strip()
    book_id = (request.args.get("book_id") or "").strip()
    requester_id = (request.args.get("requester_id") or "").strip()

    query = BookRequest.query

    if status:
        query = query.filter(BookRequest.status == status)

    if book_id:
        try:
            bid = int(book_id)
        except ValueError:
            abort(400, "book_id must be int")
        query = query.filter(BookRequest.book_id == bid)

    if requester_id:
        try:
            rid = int(requester_id)
        except ValueError:
            abort(400, "requester_id must be int")
        query = query.filter(BookRequest.requester_id == rid)

    reqs = query.order_by(BookRequest.id.desc()).limit(300).all()

    return jsonify([
        {
            "id": r.id,
            "book_id": r.book_id,
            "requester_id": r.requester_id,
            "status": r.status,
            "created_at": getattr(r, "created_at", None),
            "updated_at": getattr(r, "updated_at", None),
        }
        for r in reqs
    ])


@bp.route("/book-requests/<int:request_id>/status", methods=["PATCH"])
@login_required
@admin_required
def admin_set_request_status(request_id):
    data = _json()
    new_status = (data.get("status") or "").strip()

    if new_status not in ALLOWED_REQUEST_STATUSES:
        abort(400, "Invalid status")

    req = BookRequest.query.get_or_404(request_id)

    # moderador limitado
    if _role() == "moderator" and new_status not in {"REJECTED", "CANCELLED"}:
        abort(403)

    req.status = new_status

    # sincroniza disponibilidad del libro si toca
    if new_status == "ACCEPTED":
        book = Book.query.get_or_404(req.book_id)
        book.is_available = False
    else:
        _set_book_availability_from_requests(req.book_id)

    db.session.commit()

    return jsonify({"message": "Request updated", "id": req.id, "status": req.status})
