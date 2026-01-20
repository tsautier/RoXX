
import sqlite3
import datetime
from pathlib import Path
from roxx.utils.system import SystemManager

class CertDatabase:
    """
    Manages storage of User Client Certificates mappings.
    """
    
    @staticmethod
    def get_db_path() -> Path:
        return SystemManager.get_config_dir() / "roxx.db"

    @classmethod
    def init_db(cls):
        """Initialize the user_certificates table"""
        conn = sqlite3.connect(cls.get_db_path())
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            fingerprint TEXT UNIQUE,
            common_name TEXT,
            issuer TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(username) REFERENCES admins(username)
        )
        ''')
        conn.commit()
        conn.close()

    @classmethod
    def add_cert(cls, username: str, fingerprint: str, common_name: str, issuer: str, description: str) -> bool:
        try:
            conn = sqlite3.connect(cls.get_db_path())
            conn.execute('''
                INSERT INTO user_certificates (username, fingerprint, common_name, issuer, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, fingerprint, common_name, issuer, description))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding cert: {e}")
            return False

    @classmethod
    def get_user_certs(cls, username: str) -> list:
        conn = sqlite3.connect(cls.get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT id, fingerprint, common_name, issuer, description, created_at FROM user_certificates WHERE username = ?", (username,))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "fingerprint": r[1],
                "common_name": r[2],
                "issuer": r[3],
                "description": r[4],
                "created_at": r[5]
            }
            for r in rows
        ]

    @classmethod
    def delete_cert(cls, username: str, cert_id: int) -> bool:
        conn = sqlite3.connect(cls.get_db_path())
        conn.execute("DELETE FROM user_certificates WHERE id = ? AND username = ?", (cert_id, username))
        conn.commit()
        deleted = conn.total_changes > 0
        conn.close()
        return deleted

    @classmethod
    def get_user_by_fingerprint(cls, fingerprint: str) -> str:
        conn = sqlite3.connect(cls.get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM user_certificates WHERE fingerprint = ?", (fingerprint,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
