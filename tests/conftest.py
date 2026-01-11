import os
import sys

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from app.extensions import db
from app.models.user import User
from wsgi import app as flask_app


@pytest.fixture()
def app():
    app = flask_app
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="test-secret",
        WTF_CSRF_ENABLED=False,
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def ensure_user(user_id: int, role: str = "reader"):
    user = db.session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=f"user{user_id}@test.local",
            username=f"user{user_id}",
            role=role,
            is_active=True,
            is_blocked=False,
        )
        user.set_password("test1234")
        db.session.add(user)
        db.session.commit()
    return user


def login_session(client, user_id=1, role="reader"):
    ensure_user(user_id, role=role)
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = role
