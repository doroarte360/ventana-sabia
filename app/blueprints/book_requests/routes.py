from flask import Blueprint, request, jsonify, session, abort
from ...extensions import db
from ...models import Book, BookRequest
from ..auth.decorators import login_required

bp = Blueprint("book_requests", __name__, url_prefix="/requests")


# ---------- CREATE REQUEST ----------
@bp.post("/")
@login_required
def create_request():
    data = request.get_json(silent=True) or {}
    book_id = data.get("book_id")

    if not book_id:
        return jsonify(error="missing_fields", required=["book_id"]), 400

    # SQLAlchemy 2.x: Session.get
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify(error="book_not_found"), 404

    # opcional (recomendado): no permitir pedir libros no disponibles
    if not book.is_available:
        return jsonify(error="book_not_available"), 409

    requester_id = session["user_id"]

    if book.donor_id == requester_id:
        return jsonify(error="cannot_request_own_book"), 400

    existing = (
        BookRequest.query.filter_by(
            book_id=book.id,
            requester_id=requester_id,
            status="PENDING",
        )
        .first()
    )

    if existing:
        return jsonify(error="request_already_pending", request_id=existing.id), 409

    req = BookRequest(
        book_id=book.id,
        requester_id=requester_id,
        status="PENDING",
    )

    db.session.add(req)
    db.session.commit()

    return jsonify(
        message="created",
        id=req.id,
        book_id=req.book_id,
        requester_id=req.requester_id,
        status=req.status,
    ), 201


# ---------- MY REQUESTS ----------
@bp.get("/mine")
@login_required
def my_requests():
    user_id = session["user_id"]

    reqs = (
        BookRequest.query
        .filter_by(requester_id=user_id)
        .order_by(BookRequest.created_at.desc())
        .all()
    )

    return jsonify(
        items=[
            {
                "id": r.id,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "book": {
                    "id": r.book.id,
                    "title": r.book.title,
                    "author": r.book.author,
                    "donor_id": r.book.donor_id,
                },
            }
            for r in reqs
        ]
    ), 200


# ---------- CANCEL REQUEST (REQUESTER) ----------
@bp.patch("/<int:request_id>/cancel")
@login_required
def cancel_request(request_id):
    user_id = session["user_id"]

    # SQLAlchemy 2.x: Session.get + abort 404
    req = db.session.get(BookRequest, request_id)
    if req is None:
        abort(404)

    if req.requester_id != user_id:
        return jsonify(error="forbidden"), 403

    if req.status != "PENDING":
        return jsonify(error="invalid_state", current=req.status, allowed=["PENDING"]), 400

    req.status = "CANCELLED"

    # si no hay ACCEPTED para este libro, vuelve disponible
    has_accepted = (
        BookRequest.query
        .filter_by(book_id=req.book_id, status="ACCEPTED")
        .first()
        is not None
    )
    if not has_accepted:
        req.book.is_available = True

    db.session.commit()
    return jsonify(message="cancelled", id=req.id, status=req.status), 200


# ---------- ACCEPT / REJECT (DONOR) ----------
def _ensure_donor(req: BookRequest):
    user_id = session["user_id"]
    return req.book.donor_id == user_id


@bp.patch("/<int:request_id>/accept")
@login_required
def donor_accept(request_id):
    req = db.session.get(BookRequest, request_id)
    if req is None:
        abort(404)

    if not _ensure_donor(req):
        return jsonify(error="forbidden"), 403

    if req.status != "PENDING":
        return jsonify(error="invalid_state", current=req.status, allowed=["PENDING"]), 400

    req.status = "ACCEPTED"
    req.book.is_available = False

    db.session.commit()
    return jsonify(message="accepted", id=req.id, status=req.status), 200


@bp.patch("/<int:request_id>/reject")
@login_required
def donor_reject(request_id):
    req = db.session.get(BookRequest, request_id)
    if req is None:
        abort(404)

    if not _ensure_donor(req):
        return jsonify(error="forbidden"), 403

    if req.status != "PENDING":
        return jsonify(error="invalid_state", current=req.status, allowed=["PENDING"]), 400

    req.status = "REJECTED"

    # si no hay ACCEPTED para este libro, vuelve disponible
    has_accepted = (
        BookRequest.query
        .filter_by(book_id=req.book_id, status="ACCEPTED")
        .first()
        is not None
    )
    if not has_accepted:
        req.book.is_available = True

    db.session.commit()
    return jsonify(message="rejected", id=req.id, status=req.status), 200
