from tests.conftest import login_session

def test_non_admin_gets_403_on_admin_endpoint(client):
    login_session(client, user_id=2, role="reader")  # no admin
    res = client.get("/admin/audit")
    assert res.status_code == 403
