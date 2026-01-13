from tests.conftest import login_blocked_session


def test_blocked_user_gets_403_on_protected_endpoint(client):
    login_blocked_session(client, user_id=99, role="reader")
    res = client.get("/admin/audit")
    assert res.status_code == 403
