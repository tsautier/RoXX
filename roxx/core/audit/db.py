
import sqlite3
import json
from datetime import datetime
import logging
from roxx.utils.system import SystemManager

logger = logging.getLogger("roxx.audit.db")



class AuditDatabase:
    @staticmethod
    def get_db_path():
        """Get path to the SQLite database"""
        return SystemManager.get_config_dir() / "roxx.db"

    @classmethod
    def get_connection(cls):
        """Get a database connection"""
        return sqlite3.connect(cls.get_db_path())

    @classmethod
    def init_db(cls):
        """Initialize the audit logs table"""
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    username TEXT,
                    ip_address TEXT,
                    action TEXT NOT NULL,
                    severity TEXT DEFAULT 'INFO',
                    details TEXT -- JSON string
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Audit database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audit DB: {e}")

    @classmethod
    def log_event(cls, username: str, ip_address: str, action: str, severity: str = "INFO", details: dict = None):
        """Log an event to the database"""
        try:
            if details is None:
                details = {}
            
            conn = cls.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_logs (timestamp, username, ip_address, action, severity, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow(),
                username,
                ip_address,
                action,
                severity,
                json.dumps(details)
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    @classmethod
    def get_logs(cls, limit: int = 100, offset: int = 0, search: str = None):
        """Retrieve logs with optional search filter"""
        try:
            conn = cls.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_logs"
            params = []
            
            if search:
                query += " WHERE username LIKE ? OR action LIKE ? OR ip_address LIKE ?"
                search_term = f"%{search}%"
                params = [search_term, search_term, search_term]
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                logs.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "username": row["username"],
                    "ip_address": row["ip_address"],
                    "action": row["action"],
                    "severity": row["severity"],
                    "details": json.loads(row["details"]) if row["details"] else {}
                })
            
            conn.close()
            return logs
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            return []
