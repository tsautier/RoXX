"""
Multi-Tenant Database Management for RoXX Virtual RADIUS

Provides tenant isolation: each tenant can have its own RADIUS backends,
clients, and scoped admin users.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict

logger = logging.getLogger("roxx.auth.tenant")

DB_PATH = Path.home() / ".roxx" / "tenants.db"


class TenantDatabase:
    """
    Database manager for multi-tenant support.
    Each tenant represents an isolated RADIUS domain (Virtual RADIUS).
    """

    @staticmethod
    def init():
        """Initialize tenant database schema"""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_tenant_map (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    tenant_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(username, tenant_id),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_admin_tenant
                ON admin_tenant_map(username, tenant_id)
            """)

            conn.commit()
            logger.debug("[Tenant] Database initialized")

    @staticmethod
    def create_tenant(name: str, slug: str, description: str = "", enabled: bool = True) -> Tuple[bool, str, Optional[int]]:
        """Create a new tenant"""
        TenantDatabase.init()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.execute(
                    """INSERT INTO tenants (name, slug, description, enabled)
                       VALUES (?, ?, ?, ?)""",
                    (name, slug, description, enabled)
                )
                conn.commit()
                tenant_id = cursor.lastrowid
                logger.info(f"[Tenant] Created tenant '{name}' (ID: {tenant_id}, slug: {slug})")
                return True, "Tenant created", tenant_id
        except sqlite3.IntegrityError:
            return False, f"Tenant slug '{slug}' already exists", None
        except Exception as e:
            logger.error(f"[Tenant] Error creating tenant: {e}")
            return False, str(e), None

    @staticmethod
    def list_tenants(enabled_only: bool = False) -> List[Dict]:
        """List all tenants"""
        TenantDatabase.init()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM tenants"
            if enabled_only:
                query += " WHERE enabled = 1"
            query += " ORDER BY name ASC"
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_tenant(tenant_id: int) -> Optional[Dict]:
        """Get a tenant by ID"""
        TenantDatabase.init()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_tenant_by_slug(slug: str) -> Optional[Dict]:
        """Get a tenant by slug"""
        TenantDatabase.init()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tenants WHERE slug = ?", (slug,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_tenant(tenant_id: int, name: str = None, description: str = None, enabled: bool = None) -> Tuple[bool, str]:
        """Update tenant details"""
        TenantDatabase.init()
        updates, params = [], []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(enabled)
        if not updates:
            return False, "No updates provided"

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(tenant_id)

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(f"UPDATE tenants SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                logger.debug(f"[Tenant] Updated tenant ID {tenant_id}")
                return True, "Tenant updated"
        except Exception as e:
            logger.error(f"[Tenant] Error updating tenant: {e}")
            return False, str(e)

    @staticmethod
    def delete_tenant(tenant_id: int) -> Tuple[bool, str]:
        """Delete a tenant"""
        TenantDatabase.init()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
                conn.execute("DELETE FROM admin_tenant_map WHERE tenant_id = ?", (tenant_id,))
                conn.commit()
                logger.info(f"[Tenant] Deleted tenant ID {tenant_id}")
                return True, "Tenant deleted"
        except Exception as e:
            logger.error(f"[Tenant] Error deleting tenant: {e}")
            return False, str(e)

    @staticmethod
    def assign_admin(username: str, tenant_id: int) -> Tuple[bool, str]:
        """Assign an admin to a tenant"""
        TenantDatabase.init()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO admin_tenant_map (username, tenant_id) VALUES (?, ?)",
                    (username, tenant_id)
                )
                conn.commit()
                logger.debug(f"[Tenant] Assigned {username} to tenant {tenant_id}")
                return True, "Admin assigned to tenant"
        except Exception as e:
            logger.error(f"[Tenant] Error assigning admin: {e}")
            return False, str(e)

    @staticmethod
    def unassign_admin(username: str, tenant_id: int) -> Tuple[bool, str]:
        """Remove admin from a tenant"""
        TenantDatabase.init()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "DELETE FROM admin_tenant_map WHERE username = ? AND tenant_id = ?",
                    (username, tenant_id)
                )
                conn.commit()
                return True, "Admin removed from tenant"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_admin_tenants(username: str) -> List[Dict]:
        """Get all tenants assigned to an admin"""
        TenantDatabase.init()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT t.* FROM tenants t
                JOIN admin_tenant_map atm ON t.id = atm.tenant_id
                WHERE atm.username = ?
                ORDER BY t.name ASC
            """, (username,)).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_tenant_admins(tenant_id: int) -> List[str]:
        """Get all admins assigned to a tenant"""
        TenantDatabase.init()
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT username FROM admin_tenant_map WHERE tenant_id = ?",
                (tenant_id,)
            ).fetchall()
            return [row[0] for row in rows]
