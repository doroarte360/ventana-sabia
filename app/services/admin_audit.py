from __future__ import annotations

from flask import request
from app.extensions import db
from app.models.admin_action import AdminAction


def log_admin_action(
    *,
    admin_id: int,
    action: str,
    target_type: str,
    target_id: int | None = None,
) -> AdminAction:
    ip = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or request.remote_addr
    ua = request.headers.get("User-Agent")

    entry = AdminAction(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip,
        user_agent=ua,
    )
    db.session.add(entry)
    db.session.commit()
    return entry
