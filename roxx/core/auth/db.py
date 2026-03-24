import sqlite3
import datetime
import logging
from pathlib import Path
from roxx.utils.system import SystemManager

logger = logging.getLogger("roxx.auth.db")

_DEFAULT_DB_PATH = SystemManager.get_config_dir() / "roxx.db"
DB_PATH = _DEFAULT_DB_PATH

class AdminDatabase:
    """
    Manages the SQLite database for Admin users.
    Location: /etc/roxx/roxx.db (or local config dir in dev)
    """

    @staticmethod
    def get_db_path() -> Path:
        """Get path to the SQLite database"""
        return DB_PATH

    @classmethod
    def init_db(cls):
        """Initialize the database schema if it doesn't exist"""
        db_path = cls.get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create Admins table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            email TEXT,
            mfa_secret TEXT,
            must_change_password INTEGER DEFAULT 0,
            auth_source TEXT DEFAULT 'local',
            external_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        ''')
        
        # Simple migration: Add columns if missing (sqlite doesn't support IF NOT EXISTS for ADD COLUMN)
        try:
            cursor.execute("ALTER TABLE admins ADD COLUMN auth_source TEXT DEFAULT 'local'")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE admins ADD COLUMN external_id TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE admins ADD COLUMN phone_number TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE admins ADD COLUMN role TEXT DEFAULT 'admin'")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        conn.close()

    @classmethod
    def get_connection(cls):
        """Get a database connection"""
        return sqlite3.connect(cls.get_db_path())
    
    @classmethod
    def reset_totp(cls, username: str) -> bool:
        """Reset TOTP MFA for a user by clearing mfa_secret"""
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE admins SET mfa_secret = NULL WHERE username = ?", (username,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error resetting TOTP for {username}: {e}")
            return False
    
    @classmethod
    def get_mfa_status(cls, username: str) -> dict:
        """Get MFA status for a user"""
        conn = cls.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT mfa_secret, phone_number FROM admins WHERE username = ?", 
            (username,)
        ).fetchone()
        conn.close()
        
        if not row:
            return {"totp_enabled": False, "sms_enabled": False}
        
        return {
            "totp_enabled": bool(row['mfa_secret']),
            "sms_enabled": bool(row['phone_number'])
        }

    @classmethod
    def get_role(cls, username: str) -> str:
        """Get the role for a user. Returns 'admin' as default."""
        conn = cls.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT role FROM admins WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()
        if not row:
            return 'admin'
        return row['role'] or 'admin'

    @classmethod
    def set_role(cls, username: str, role: str) -> bool:
        """Set the role for a user."""
        valid_roles = ('superadmin', 'admin', 'auditor')
        if role not in valid_roles:
            logger.error(f"Invalid role '{role}'. Must be one of {valid_roles}")
            return False
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE admins SET role = ? WHERE username = ?", (role, username))
            conn.commit()
            conn.close()
            logger.debug(f"[RBAC] Set role for {username} to {role}")
            return True
        except Exception as e:
            logger.error(f"Error setting role for {username}: {e}")
            return False
