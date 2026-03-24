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
from functools import wraps

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
        Action.MANAGE_ADMINS,
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


def check_permission(role: str, action: str) -> bool:
    """Check if a role has permission to perform an action."""
    perms = ROLE_PERMISSIONS.get(role, set())
    has_perm = action in perms
    logger.debug(f"[RBAC] check_permission role={role} action={action} -> {has_perm}")
    return has_perm


def get_role_from_session(request: Request) -> Optional[str]:
    """
    Extract role from session cookie.
    Cookie format: base64(username:status:role)
    Falls back to 'admin' for legacy cookies without role.
    """
    import base64
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return None
    try:
        decoded = base64.b64decode(session_cookie).decode("utf-8")
        parts = decoded.split(":")
        if len(parts) >= 3:
            return parts[2]
        elif len(parts) == 2:
            # Legacy cookie without role — fallback
            return Role.ADMIN
    except Exception:
        pass
    return None


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory that checks if the current user has one of the allowed roles.

    Usage:
        @app.post("/api/admins", dependencies=[Depends(require_role('superadmin', 'admin'))])
    """
    async def _dependency(request: Request):
        import base64
        session_cookie = request.cookies.get("session")
        if not session_cookie:
            raise HTTPException(status_code=401, detail="Not authenticated")

        try:
            decoded = base64.b64decode(session_cookie).decode("utf-8")
            parts = decoded.split(":")
            username = parts[0]
            status = parts[1] if len(parts) > 1 else None
            role = parts[2] if len(parts) > 2 else Role.ADMIN

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

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[RBAC] Session parsing error: {e}")
            raise HTTPException(status_code=401, detail="Invalid session")

    return _dependency
