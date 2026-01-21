
import sqlite3
import json
from datetime import datetime
import logging
from roxx.utils.system import SystemManager

logger = logging.getLogger("roxx.audit.db")

def get_db_path():
    return SystemManager.get_config_dir() / "roxx.db"

class AuditDatabase:
    @staticmethod
    def init_db():
        """Initialize the audit logs table"""
        try:
            conn = sqlite3.connect(get_db_path())
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

    @staticmethod
    def log_event(username: str, ip_address: str, action: str, severity: str = "INFO", details: dict = None):
        """Log an event to the database"""
        try:
            if details is None:
                details = {}
            
            conn = sqlite3.connect(get_db_path())
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

    @staticmethod
    def get_logs(limit: int = 100, offset: int = 0, search: str = None):
        """Retrieve logs with optional search filter"""
        try:
            conn = sqlite3.connect(get_db_path())
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
