# app/security/permissions.py
from __future__ import annotations

from typing import Optional

# Permisos (strings)
P_USERS_READ = "users:read"
P_USERS_UPDATE_ROLE = "users:update_role"
P_USERS_UPDATE_STATUS = "users:update_status"
P_BOOKS_UPDATE_AVAILABILITY = "books:update_availability"
P_REQUESTS_UPDATE_STATUS = "requests:update_status"
P_AUDIT_READ = "audit:read"

# Endpoint -> permiso requerido
# (endpoint names según flask routes: blueprint.endpoint)
ENDPOINT_PERMISSIONS: dict[str, str] = {
    # admin
    "admin.admin_set_user_role": P_USERS_UPDATE_ROLE,
    "admin.admin_set_user_status": P_USERS_UPDATE_STATUS,
    "admin.admin_set_book_availability": P_BOOKS_UPDATE_AVAILABILITY,
    "admin.admin_set_request_status": P_REQUESTS_UPDATE_STATUS,
    "admin.admin_list_audit": P_AUDIT_READ,
}

# Role -> permisos concedidos (v1.3)
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "reader": set(),
    # moderator (si aún no existe, no pasa nada; lo dejamos preparado)
    "moderator": {P_REQUESTS_UPDATE_STATUS, P_BOOKS_UPDATE_AVAILABILITY},
    # admin se resuelve por override en access.py (o podrías poner "*" aquí)
    "admin": set(),
}


def get_required_permission(endpoint: str | None, method: str) -> Optional[str]:
    """
    Devuelve el permiso requerido para un endpoint.
    - Si el endpoint no está en el mapa, no exige permiso (fallback a Rule-based).
    - Si quieres condicionar por método, aquí es donde se haría.
    """
    if not endpoint:
        return None

    # Si un endpoint necesita permiso, lo necesita para cualquier método (normalmente PATCH/POST).
    # Si quisieras: if method in {"GET"}: ... etc.
    return ENDPOINT_PERMISSIONS.get(endpoint)


def role_has_permission(role: str | None, permission: str) -> bool:
    if not role:
        return False
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms
