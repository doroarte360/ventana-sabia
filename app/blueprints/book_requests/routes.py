from flask import Blueprint, request, jsonify, session
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

    book = Book.query.get(book_id)
    if not book:
        return jsonify(error="book_not_found"), 404

    requester_id = session["user_id"]

    if book.donor_id == requester_id:
        return jsonify(error="cannot_request_own_book"), 400

    existing = BookRequest.query.filter_by(
        book_id=book.id,
        requester_id=requester_id,
        status="pending"
    ).first()

    if existing:
        return jsonify(
            error="request_already_pending",
            request_id=existing.id
        ), 409

    req = BookRequest(
        book_id=book.id,
        requester_id=requester_id,
        status="pending"
    )

    db.session.add(req)
    db.session.commit()

    return jsonify(
        message="created",
        id=req.id,
        book_id=req.book_id,
        requester_id=req.requester_id,
        status=req.status
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
