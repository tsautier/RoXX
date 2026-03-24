"""
Role-Based Access Control (RBAC) for RoXX Admins

Roles:
  - superadmin: Full access (manage admins, roles, system config, tenants)
  - admin:      Standard admin (manage RADIUS users/backends, MFA, view logs)
  - auditor:    Read-only (view dashboard, logs, system info — no mutations)
"""

import logging
from enum import Enum
from typing import Set, Optional

from fastapi import Request, HTTPException

logger = logging.getLogger("roxx.auth.rbac")


class Role(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    AUDITOR = "auditor"


# Action constants
class Action:
    # Admin management
    MANAGE_ADMINS = "manage_admins"
    CHANGE_ROLES = "change_roles"
    DELETE_ADMINS = "delete_admins"

    # RADIUS / Backends
    MANAGE_RADIUS_USERS = "manage_radius_users"
    MANAGE_RADIUS_BACKENDS = "manage_radius_backends"
    MANAGE_RADIUS_CLIENTS = "manage_radius_clients"

    # Auth providers
    MANAGE_AUTH_PROVIDERS = "manage_auth_providers"

    # MFA
    MANAGE_MFA = "manage_mfa"

    # System
    MANAGE_SYSTEM_CONFIG = "manage_system_config"
    MANAGE_SSL = "manage_ssl"
    MANAGE_PKI = "manage_pki"
    MANAGE_API_TOKENS = "manage_api_tokens"

    # Tenants
    MANAGE_TENANTS = "manage_tenants"

    # Read-only
    VIEW_DASHBOARD = "view_dashboard"
    VIEW_LOGS = "view_logs"
    VIEW_SYSTEM_INFO = "view_system_info"


# Permission matrix
ROLE_PERMISSIONS: dict[str, Set[str]] = {
    Role.SUPERADMIN: {
        Action.MANAGE_ADMINS,
        Action.CHANGE_ROLES,
        Action.DELETE_ADMINS,
        Action.MANAGE_RADIUS_USERS,
        Action.MANAGE_RADIUS_BACKENDS,
        Action.MANAGE_RADIUS_CLIENTS,
        Action.MANAGE_AUTH_PROVIDERS,
        Action.MANAGE_MFA,
        Action.MANAGE_SYSTEM_CONFIG,
        Action.MANAGE_SSL,
        Action.MANAGE_PKI,
        Action.MANAGE_API_TOKENS,
        Action.MANAGE_TENANTS,
        Action.VIEW_DASHBOARD,
        Action.VIEW_LOGS,
        Action.VIEW_SYSTEM_INFO,
    },
    Role.ADMIN: {
        Action.MANAGE_RADIUS_USERS,
        Action.MANAGE_RADIUS_BACKENDS,
        Action.MANAGE_RADIUS_CLIENTS,
        Action.MANAGE_AUTH_PROVIDERS,
        Action.MANAGE_MFA,
        Action.MANAGE_API_TOKENS,
        Action.VIEW_DASHBOARD,
        Action.VIEW_LOGS,
        Action.VIEW_SYSTEM_INFO,
    },
    Role.AUDITOR: {
        Action.VIEW_DASHBOARD,
        Action.VIEW_LOGS,
        Action.VIEW_SYSTEM_INFO,
    },
}


def _resolve_role(username: str) -> str:
    from roxx.core.auth.db import AdminDatabase
    return AdminDatabase.get_role(username)


def get_auth_context(request: Request) -> Optional[dict]:
    """
    Return the authenticated session context from the signed Starlette session.
    Legacy unsigned cookies are migrated lazily, but role is always resolved
    server-side from the database.
    """
    auth = request.session.get("auth")
    if isinstance(auth, dict):
        username = auth.get("username")
        status = auth.get("status")
        if username and status:
            role = _resolve_role(username) if status == "active" else auth.get("role")
            return {"username": username, "status": status, "role": role}

    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return None

    try:
        import base64

        decoded = base64.b64decode(session_cookie).decode("utf-8")
        parts = decoded.split(":")
        if len(parts) < 2:
            return None

        username = parts[0]
        status = parts[1]
        role = _resolve_role(username) if status == "active" else None
        auth = {"username": username, "status": status, "role": role}
        request.session["auth"] = auth
        return auth
    except Exception:
        return None


def set_auth_context(request: Request, username: str, status: str) -> dict:
    """Persist the signed auth context in the server session."""
    role = _resolve_role(username) if status == "active" else None
    auth = {"username": username, "status": status, "role": role}
    request.session["auth"] = auth
    return auth


def clear_auth_context(request: Request) -> None:
    request.session.pop("auth", None)


def check_permission(role: str, action: str) -> bool:
    """Check if a role has permission to perform an action."""
    perms = ROLE_PERMISSIONS.get(role, set())
    has_perm = action in perms
    logger.debug(f"[RBAC] check_permission role={role} action={action} -> {has_perm}")
    return has_perm


def get_role_from_session(request: Request) -> Optional[str]:
    auth = get_auth_context(request)
    return auth.get("role") if auth else None


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory that checks if the current user has one of the allowed roles.

    Usage:
        @app.post("/api/admins", dependencies=[Depends(require_role('superadmin', 'admin'))])
    """
    async def _dependency(request: Request):
        auth = get_auth_context(request)
        if not auth:
            raise HTTPException(status_code=401, detail="Not authenticated")

        username = auth["username"]
        status = auth["status"]
        role = auth.get("role") or Role.ADMIN

        if status != "active":
            raise HTTPException(status_code=401, detail="Session not active")

        if role not in allowed_roles:
            logger.warning(f"[RBAC] Access denied for {username} (role={role}), required={allowed_roles}")
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}"
            )

        logger.debug(f"[RBAC] Access granted for {username} (role={role})")
        return username

    return _dependency


def require_action(action: str):
    async def _dependency(request: Request):
        auth = get_auth_context(request)
        if not auth:
            raise HTTPException(status_code=401, detail="Not authenticated")

        if auth["status"] != "active":
            raise HTTPException(status_code=401, detail="Session not active")

        role = auth.get("role") or Role.ADMIN
        if not check_permission(role, action):
            raise HTTPException(status_code=403, detail=f"Missing permission: {action}")
        return auth["username"]

    return _dependency
