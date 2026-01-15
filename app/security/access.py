from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from flask import Request

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

@dataclass(frozen=True)
class Rule:
    blueprint: str | None  # None = cualquiera
    methods: set[str]      # {"GET"} o {"POST","PATCH"} o {"*"}
    roles: set[str]        # {"reader","admin"} etc.

def _method_match(rule_methods: set[str], method: str) -> bool:
    return "*" in rule_methods or method in rule_methods

def is_public_endpoint(endpoint: str | None) -> bool:
    if not endpoint:
        return False
    if endpoint.startswith("auth."):
        return True
    if endpoint in {"health", "index", "routes"}:
        return True
    return False

def check_access(user, req: Request, rules: Iterable[Rule]) -> bool:
    # admin override (se mantiene)
    if getattr(user, "role", None) == "admin":
        return True

    # ✅ v1.3: permiso por endpoint (si aplica)
    from .permissions import get_required_permission, role_has_permission

    required = get_required_permission(req.endpoint, req.method)
    if required:
        return role_has_permission(getattr(user, "role", None), required)

    # ✅ fallback: reglas actuales (compat)
    bp = req.blueprint
    method = req.method
    role = getattr(user, "role", None)

    for r in rules:
        if r.blueprint is not None and r.blueprint != bp:
            continue
        if not _method_match(r.methods, method):
            continue
        if role in r.roles:
            return True

    return False
