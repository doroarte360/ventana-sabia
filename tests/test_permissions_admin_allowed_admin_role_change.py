from tests.conftest import login_session, ensure_user


def test_admin_can_change_user_role(client):
    # login as admin
    login_session(client, user_id=10, role="admin")

    # target user exists
    target = ensure_user(11, role="reader", is_active=True, is_blocked=False)

    resp = client.patch(
        f"/admin/users/{target.id}/role",
        json={"role": "moderator"},
    )

    assert resp.status_code in (200, 204)

    # Optional: if endpoint returns JSON, you can assert something like:
    # if resp.status_code == 200:
    #     data = resp.get_json()
    #     assert data is not None
