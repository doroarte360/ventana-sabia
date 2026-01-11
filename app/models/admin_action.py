
from datetime import datetime
from app.extensions import db


class AdminAction(db.Model):
    __tablename__ = "admin_actions"

    id = db.Column(db.Integer, primary_key=True)

    # Quién hizo la acción (admin)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    admin = db.relationship("User", backref=db.backref("admin_actions", lazy="dynamic"))

    # Qué hizo
    action = db.Column(db.String(80), nullable=False, index=True)
    # Sobre qué entidad
    target_type = db.Column(db.String(30), nullable=False, index=False)  # "user" | "book" | "request" ...
    target_id = db.Column(db.Integer, nullable=True, index=False)        # id del target (si aplica)

    # Contexto mínimo
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6
    user_agent = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        db.Index("ix_admin_actions_target", "target_type", "target_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }

    # (Opcional) Constantes para evitar strings sueltos
    class Actions:
        USER_BLOCK = "user.block"
        USER_UNBLOCK = "user.unblock"
        USER_ROLE_CHANGE = "user.role_change"
        USER_SOFT_DELETE = "user.soft_delete"

        BOOK_HIDE = "book.hide"
        BOOK_UNHIDE = "book.unhide"
        BOOK_FLAG = "book.flag"

        REQUEST_FORCE_CLOSE = "request.force_close"
        REQUEST_ACCEPT = "request.accept"
        REQUEST_REJECT = "request.reject"
        REQUEST_CANCEL = "request.cancel"
