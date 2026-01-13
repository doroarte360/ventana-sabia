from tests.conftest import login_session, login_blocked_session


def test_enforcement_requires_login_for_private_endpoints(client):
    # tu /books redirige (308) probablemente a /books/
    res = client.get("/books/", follow_redirects=False)
    assert res.status_code == 401


def test_enforcement_allows_public_endpoints_without_login(client):
    res = client.get("/health")
    assert res.status_code == 200


def test_enforcement_forbids_admin_blueprint_for_non_admin(client):
    login_session(client)  # user normal
    res = client.get("/admin/audit")
    assert res.status_code == 403


def test_enforcement_forbids_blocked_user_everywhere(client):
    login_blocked_session(client)
    res = client.get("/books/", follow_redirects=False)
    assert res.status_code == 403


def test_enforcement_allows_admin_blueprint_for_admin(client):
    login_session(client, role="admin")
    res = client.get("/admin/audit")
    assert res.status_code in (200, 204)
