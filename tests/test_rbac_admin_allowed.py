from tests.conftest import login_session

def test_admin_gets_200_on_admin_endpoint(client):
    login_session(client, user_id=3, role="admin")
    res = client.get("/admin/audit")
    assert res.status_code == 200

