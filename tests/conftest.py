import os
import sys

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models.user import User


@pytest.fixture()
def app():
    from app import create_app

    config_overrides = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    }

    # ✅ IMPORTANT: pass overrides INTO create_app
    app = create_app(config_overrides=config_overrides)

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def ensure_user(user_id: int, role: str = "reader", is_active: bool = True, is_blocked: bool = False):
    user = db.session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=f"user{user_id}@test.local",
            username=f"user{user_id}",
            role=role,
            is_active=is_active,
            is_blocked=is_blocked,
        )
        user.set_password("test1234")
        db.session.add(user)
        db.session.commit()
    else:
        user.role = role
        user.is_active = is_active
        user.is_blocked = is_blocked
        db.session.commit()
    return user


def login_blocked_session(client, user_id=99, role="reader"):
    ensure_user(user_id, role=role, is_active=True, is_blocked=True)
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = role

def login_session(client, user_id=1, role="reader"):
    ensure_user(user_id, role=role, is_active=True, is_blocked=False)
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = role
