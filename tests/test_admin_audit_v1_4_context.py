from app.extensions import db
from app.models.admin_action import AdminAction
from tests.conftest import login_session, ensure_user


def test_admin_role_change_logs_context_and_details(client, app):
    login_session(client, user_id=10, role="admin")
    target = ensure_user(11, role="reader", is_active=True, is_blocked=False)

    resp = client.patch(f"/admin/users/{target.id}/role", json={"role": "moderator"})
    assert resp.status_code == 200

    with app.app_context():
        row = db.session.query(AdminAction).order_by(AdminAction.id.desc()).first()
        assert row is not None

        assert row.admin_id == 10
        assert row.target_type == "user"
        assert row.target_id == target.id

        assert row.endpoint == "admin.admin_set_user_role"
        assert row.method == "PATCH"
        assert row.path == f"/admin/users/{target.id}/role"

        assert row.details is not None
        assert row.details.get("old_role") == "reader"
        assert row.details.get("new_role") == "moderator"
