import sqlite3
import datetime
from pathlib import Path
from roxx.utils.system import SystemManager

class AdminDatabase:
    """
    Manages the SQLite database for Admin users.
    Location: /etc/roxx/roxx.db (or local config dir in dev)
    """

    @staticmethod
    def get_db_path() -> Path:
        """Get path to the SQLite database"""
        return SystemManager.get_config_dir() / "roxx.db"

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
        
        conn.commit()
        conn.close()

    @classmethod
    def get_connection(cls):
        """Get a database connection"""
        return sqlite3.connect(cls.get_db_path())
