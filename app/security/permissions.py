# app/security/permissions.py
from __future__ import annotations
from typing import Optional

# Permisos (strings)
P_USERS_READ = "users:read"
P_USERS_UPDATE_ROLE = "users:update_role"
P_USERS_UPDATE_STATUS = "users:update_status"
P_USERS_UPDATE_BLOCK = "users:update_block"  # si vas a proteger /block

P_BOOKS_READ = "books:read"
P_BOOKS_UPDATE_AVAILABILITY = "books:update_availability"

P_REQUESTS_READ = "requests:read"
P_REQUESTS_REJECT = "requests:reject"
P_REQUESTS_ACCEPT = "requests:accept"

# (nota: status genérico ya no hace falta para admin_set_request_status)

P_AUDIT_READ = "audit:read"
P_SECURITY_EVENTS_READ = "security_events:read"

ENDPOINT_PERMISSIONS: dict[str, str] = {
    # admin reads
    "admin.admin_list_users": P_USERS_READ,
    "admin.admin_list_books": P_BOOKS_READ,
    "admin.admin_list_book_requests": P_REQUESTS_READ,
    "admin.admin_list_audit": P_AUDIT_READ,
    "admin.admin_list_security_events": P_SECURITY_EVENTS_READ,

    # admin writes (fijos por endpoint)
    "admin.admin_set_user_role": P_USERS_UPDATE_ROLE,
    "admin.admin_set_user_status": P_USERS_UPDATE_STATUS,
    "admin.admin_set_user_block": P_USERS_UPDATE_BLOCK,
    "admin.admin_set_book_availability": P_BOOKS_UPDATE_AVAILABILITY,

    # Nota: admin.admin_set_request_status NO va aquí (depende del new_status)
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "reader": {
        # si “reader” puede ver admin en modo lectura:
        P_USERS_READ, P_BOOKS_READ, P_REQUESTS_READ, P_AUDIT_READ, P_SECURITY_EVENTS_READ
    },
    "moderator": {
        P_USERS_READ, P_BOOKS_READ, P_REQUESTS_READ,
        P_AUDIT_READ, P_SECURITY_EVENTS_READ,

        P_BOOKS_UPDATE_AVAILABILITY,
        P_USERS_UPDATE_STATUS,
        P_USERS_UPDATE_BLOCK,

        P_REQUESTS_REJECT,  # ✅ solo rechazar
        # P_REQUESTS_APPROVE no
    },
    "admin": {"*"},
}

def get_required_permission(endpoint: str | None, method: str) -> Optional[str]:
    if not endpoint:
        return None
    return ENDPOINT_PERMISSIONS.get(endpoint)

def role_has_permission(role: str | None, permission: str) -> bool:
    if not role:
        return False
    perms = ROLE_PERMISSIONS.get(role, set())
    return ("*" in perms) or (permission in perms)
