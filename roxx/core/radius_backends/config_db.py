"""
Database schema and manager for RADIUS backend configuration
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("roxx.radius_backends.db")

# Database path
DB_PATH = Path.home() / ".roxx" / "radius_backends.db"


class RadiusBackendDB:
    """
    Database manager for RADIUS authentication backend configurations.
    
    Stores configuration for LDAP, SQL, and file-based backends.
    """
    
    @staticmethod
    def init():
        """Initialize database and create tables if they don't exist"""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS radius_backends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backend_type TEXT NOT NULL CHECK(backend_type IN ('ldap', 'ntlm', 'sql', 'file')),
                   name TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    priority INTEGER DEFAULT 100,
                    config_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(backend_type, name)
                )
            """)
            
            # Create index on priority for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_radius_backends_priority 
                ON radius_backends(priority, enabled)
            """)
            
            conn.commit()
            logger.info(f"RADIUS backends database initialized at {DB_PATH}")
    
    @staticmethod
    def list_backends(backend_type: Optional[str] = None, enabled_only: bool = False) -> List[dict]:
        """
        List all configured backends.
        
        Args:
            backend_type: Filter by type ('ldap', 'ntlm', 'sql', 'file'). None = all types.
            enabled_only: If True, return only enabled backends
            
        Returns:
            List of backend dictionaries, ordered by priority (lower = higher priority)
        """
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT id, backend_type, name, enabled, priority, config_json, 
                       created_at, updated_at
                FROM radius_backends
                WHERE 1=1
            """
            params = []
            
            if backend_type:
                query += " AND backend_type = ?"
                params.append(backend_type)
            
            if enabled_only:
                query += " AND enabled = 1"
            
            query += " ORDER BY priority ASC, id ASC"
            
            rows = conn.execute(query, params).fetchall()
            
            backends = []
            for row in rows:
                backend = dict(row)
                backend['config'] = json.loads(backend['config_json'])
                del backend['config_json']
                backends.append(backend)
            
            return backends
    
    @staticmethod
    def get_backend(backend_id: int) -> Optional[dict]:
        """Get backend by ID"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            
            row = conn.execute(
                """SELECT id, backend_type, name, enabled, priority, config_json,
                         created_at, updated_at
                   FROM radius_backends WHERE id = ?""",
                (backend_id,)
            ).fetchone()
            
            if row:
                backend = dict(row)
                backend['config'] = json.loads(backend['config_json'])
                del backend['config_json']
                return backend
            return None
    
    @staticmethod
    def create_backend(backend_type: str, name: str, config_dict: dict, 
                      enabled: bool = True, priority: int = 100) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new backend configuration.
        
        Returns:
            (success, message, backend_id)
        """
        if backend_type not in ['ldap', 'ntlm', 'sql', 'file']:
            return False, f"Invalid backend type: {backend_type}", None
        
        config_json = json.dumps(config_dict)
        
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.execute(
                    """INSERT INTO radius_backends 
                       (backend_type, name, enabled, priority, config_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (backend_type, name, enabled, priority, config_json)
                )
                conn.commit()
                backend_id = cursor.lastrowid
                logger.info(f"Created {backend_type} backend '{name}' with ID {backend_id}")
                return True, f"Backend created successfully", backend_id
        except sqlite3.IntegrityError:
            return False, f"Backend '{name}' of type '{backend_type}' already exists", None
        except Exception as e:
            logger.error(f"Error creating backend: {e}")
            return False, f"Database error: {str(e)}", None
    
    @staticmethod
    def update_backend(backend_id: int, name: Optional[str] = None,
                      config_dict: Optional[dict] = None,
                      enabled: Optional[bool] = None,
                      priority: Optional[int] = None) -> Tuple[bool, str]:
        """Update backend configuration"""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if config_dict is not None:
            updates.append("config_json = ?")
            params.append(json.dumps(config_dict))
        
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(enabled)
        
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        
        if not updates:
            return False, "No updates provided"
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(backend_id)
        
        try:
            with sqlite3.connect(DB_PATH) as conn:
                query = f"UPDATE radius_backends SET {', '.join(updates)} WHERE id = ?"
                conn.execute(query, params)
                conn.commit()
                logger.info(f"Updated backend ID {backend_id}")
                return True, "Backend updated successfully"
        except Exception as e:
            logger.error(f"Error updating backend: {e}")
            return False, f"Database error: {str(e)}"
    
    @staticmethod
    def delete_backend(backend_id: int) -> Tuple[bool, str]:
        """Delete backend configuration"""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("DELETE FROM radius_backends WHERE id = ?", (backend_id,))
                conn.commit()
                logger.info(f"Deleted backend ID {backend_id}")
                return True, "Backend deleted successfully"
        except Exception as e:
            logger.error(f"Error deleting backend: {e}")
            return False, f"Database error: {str(e)}"
    
    @staticmethod
    def update_priorities(priority_map: dict) -> Tuple[bool, str]:
        """
        Update priorities for multiple backends.
        
        Args:
            priority_map: Dict of {backend_id: priority}
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                for backend_id, priority in priority_map.items():
                    conn.execute(
                        "UPDATE radius_backends SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (priority, backend_id)
                    )
                conn.commit()
                logger.info(f"Updated priorities for {len(priority_map)} backends")
                return True, "Priorities updated successfully"
        except Exception as e:
            logger.error(f"Error updating priorities: {e}")
            return False, f"Database error: {str(e)}"
