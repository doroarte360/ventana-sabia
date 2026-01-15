from tests.conftest import login_session, ensure_user


def test_reader_cannot_change_user_role(client):
    # login as reader
    login_session(client, user_id=1, role="reader")

    # target user exists
    target = ensure_user(2, role="reader", is_active=True, is_blocked=False)

    resp = client.patch(
        f"/admin/users/{target.id}/role",
        json={"role": "moderator"},
    )

    assert resp.status_code == 403
    data = resp.get_json()
    assert data and data.get("error") == "forbidden"
