from tests.conftest import login_session
from app.extensions import db
from app.models import Book


def test_books_search_filters(client):
    login_session(client, user_id=1)

    r1 = client.post("/books/", json={
        "title": "Libro 2",
        "author": "Autor",
        "genre": "Test",
        "language": "es",
        "description": "x",
    })
    assert r1.status_code == 201

    r2 = client.post("/books/", json={
        "title": "El Quijote",
        "author": "Cervantes",
        "genre": "Novela",
        "language": "es",
        "description": "x",
    })
    assert r2.status_code == 201

    # Forzamos que El Quijote NO esté disponible
    with client.application.app_context():
        b = Book.query.filter_by(title="El Quijote").first()
        b.is_available = False
        db.session.commit()

    res = client.get("/books/search?q=Libro&available=true")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Libro 2"

