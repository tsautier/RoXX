"""
Database manager for WebAuthn credentials
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("roxx.auth.webauthn.db")

# Database path
DB_PATH = Path.home() / ".roxx" / "webauthn.db"

class WebAuthnDatabase:
    """
    Database for storing FIDO2/WebAuthn credentials.
    """
    
    @staticmethod
    def init():
        """Initialize database"""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    credential_id BLOB NOT NULL,
                    public_key BLOB NOT NULL,
                    sign_count INTEGER DEFAULT 0,
                    credential_name TEXT,
                    transports TEXT,  -- JSON list of transports (usb, nfc, ble, internal)
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    UNIQUE(user_id, credential_name),
                    UNIQUE(credential_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_credentials_user 
                ON credentials(user_id)
            """)
            
            conn.commit()
            logger.info(f"WebAuthn database initialized at {DB_PATH}")

    @staticmethod
    def list_credentials(user_id: str) -> List[dict]:
        """List credentials for a user"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM credentials WHERE user_id = ? ORDER BY created_at DESC", 
                (user_id,)
            ).fetchall()
            
            creds = []
            for row in rows:
                c = dict(row)
                if c['transports']:
                   try:
                       c['transports'] = json.loads(c['transports'])
                   except:
                       c['transports'] = []
                creds.append(c)
            return creds

    @staticmethod
    def add_credential(user_id: str, credential_id: bytes, public_key: bytes, sign_count: int, name: str, transports: List[str] = None):
        """Add a new credential"""
        transports_json = json.dumps(transports) if transports else "[]"
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """INSERT INTO credentials 
                       (user_id, credential_id, public_key, sign_count, credential_name, transports)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, credential_id, public_key, sign_count, name, transports_json)
                )
                conn.commit()
                return True, "Credential added successfully"
        except sqlite3.IntegrityError:
            return False, "Credential name already exists or duplicate ID"
        except Exception as e:
            logger.error(f"Error adding credential: {e}")
            return False, str(e)

    @staticmethod
    def delete_credential(cred_db_id: int, user_id: str):
        """Delete a credential"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM credentials WHERE id = ? AND user_id = ?", (cred_db_id, user_id))
            conn.commit()
            return True

    @staticmethod
    def get_credential_by_id(credential_id: bytes):
        """Get credential by its unique Byte ID (for authentication verify)"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM credentials WHERE credential_id = ?", (credential_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_sign_count(cred_db_id: int, new_count: int):
        """Update signature counter after successful login"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE credentials SET sign_count = ?, last_used_at = CURRENT_TIMESTAMP WHERE id = ?", 
                (new_count, cred_db_id)
            )
            conn.commit()

