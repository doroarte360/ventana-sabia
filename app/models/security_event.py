from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


class SecurityEvent(db.Model):
    __tablename__ = "security_events"

    id = db.Column(db.Integer, primary_key=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # "deny_unauthorized" | "deny_blocked" | "deny_forbidden" | "rate_limited"
    event_type = db.Column(db.String(32), nullable=False, index=True)

    status_code = db.Column(db.Integer, nullable=False, index=True)

    endpoint = db.Column(db.String(128), nullable=True, index=True)
    blueprint = db.Column(db.String(64), nullable=True, index=True)
    method = db.Column(db.String(10), nullable=True)
    path = db.Column(db.String(255), nullable=True)

    user_id = db.Column(db.Integer, nullable=True, index=True)
    role = db.Column(db.String(32), nullable=True, index=True)

    ip = db.Column(db.String(64), nullable=True, index=True)

    details = db.Column(db.Text, nullable=True)
