from __future__ import annotations

from flask import Request, session, current_app

from app.extensions import db
from app.models.security_event import SecurityEvent


def _client_ip(req: Request) -> str | None:
    xff = req.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return req.remote_addr


def record_security_event(
    *,
    event_type: str,
    status_code: int,
    req: Request,
    user=None,
    details: str | None = None,
) -> None:
    """
    Best-effort: nunca debe romper la request.
    En TESTING: no guarda (para no ensuciar tests).
    """
    try:
        if current_app.config.get("TESTING"):
            return

        user_id = session.get("user_id") or getattr(user, "id", None)
        role = getattr(user, "role", None) if user else session.get("role")

        ev = SecurityEvent(
            event_type=event_type,
            status_code=status_code,
            endpoint=req.endpoint,
            blueprint=req.blueprint,
            method=req.method,
            path=req.path,
            user_id=user_id,
            role=role,
            ip=_client_ip(req),
            details=details,
        )
        db.session.add(ev)
        db.session.commit()
    except Exception:
        db.session.rollback()
