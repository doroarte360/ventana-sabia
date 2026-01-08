from flask import Blueprint, jsonify, request, session
from ...extensions import db
from ...models import Book
from ..auth.decorators import login_required

bp = Blueprint("books", __name__, url_prefix="/books")


@bp.get("/ping")
@login_required
def ping_books():
    return jsonify(ok=True, area="books")


@bp.post("/")
@login_required
def create_book():
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    author = (data.get("author") or "").strip()
    genre = (data.get("genre") or "").strip() or None
    language = (data.get("language") or "").strip() or None
    description = (data.get("description") or "").strip() or None

    if not title or not author:
        return jsonify(
            error="missing_fields",
            required=["title", "author"]
        ), 400

    book = Book(
        title=title,
        author=author,
        genre=genre,
        language=language,
        description=description,
        donor_id=session["user_id"],  # 🔐 viene de la sesión
        is_available=True
    )

    db.session.add(book)
    db.session.commit()

    return jsonify(
        message="created",
        id=book.id,
        title=book.title,
        author=book.author,
        donor_id=book.donor_id
    ), 201

@bp.get("/")
def list_books():
    books = Book.query.order_by(Book.created_at.desc()).all()

    return jsonify(
        items=[
            {
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "genre": b.genre,
                "language": b.language,
                "is_available": b.is_available,
                "donor_id": b.donor_id,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in books
        ]
    ), 200


@bp.get("/<int:book_id>")
def get_book(book_id: int):
    book = Book.query.get(book_id)
    if not book:
        return jsonify(error="not_found"), 404

    return jsonify(
        id=book.id,
        title=book.title,
        author=book.author,
        genre=book.genre,
        language=book.language,
        description=book.description,
        cover_path=book.cover_path,
        is_available=book.is_available,
        donor_id=book.donor_id,
        created_at=book.created_at.isoformat() if book.created_at else None,
        updated_at=book.updated_at.isoformat() if book.updated_at else None,
    ), 200

