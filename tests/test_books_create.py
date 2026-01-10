from tests.conftest import login_session


def test_create_book_requires_fields(client):
    login_session(client, user_id=1)

    r = client.post("/books/", json={"title": "", "author": ""})
    assert r.status_code == 400
    data = r.get_json()
    assert data["error"] == "missing_fields"


def test_create_book_sets_donor_and_available(client):
    login_session(client, user_id=7)

    r = client.post("/books/", json={
        "title": "X",
        "author": "Y",
        "genre": "Test",
        "language": "es",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["donor_id"] == 7
