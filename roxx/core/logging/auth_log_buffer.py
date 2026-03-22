"""
Authentication Log Buffer

Thread-safe circular buffer for storing recent authentication events.
Used for debugging Auth Providers and RADIUS Backends.
"""

from collections import deque
from threading import Lock
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger("roxx.logging")


class AuthLogBuffer:
    """
    Thread-safe circular buffer for authentication logs.
    
    Stores recent authentication events (success and failures) for debugging.
    Automatically prunes old entries when max size is reached.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize log buffer.
        
        Args:
            max_size: Maximum number of log entries to retain
        """
        self._buffer = deque(maxlen=max_size)
        self._lock = Lock()
        self.max_size = max_size
    
    def add(self, entry: Dict[str, Any]):
        """
        Add a log entry to the buffer.
        
        Entry should contain:
        - backend_type: str
        - backend_name: str (optional)
        - username: str
        - action: str (e.g., 'authenticate', 'test_connection')
        - success: bool
        - duration_ms: float (optional)
        - details: str (optional)
        - source_ip: str (optional)
        
        Timestamp is automatically added.
        
        Args:
            entry: Dictionary containing log data
        """
        with self._lock:
            # Add timestamp if not present
            if 'timestamp' not in entry:
                entry['timestamp'] = datetime.utcnow().isoformat() + 'Z'
            
            self._buffer.append(entry)
    
    def get_logs(self, 
                 limit: int = 100,
                 backend_type: Optional[str] = None,
                 backend_name: Optional[str] = None,
                 success: Optional[bool] = None,
                 username: Optional[str] = None,
                 since: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve logs with optional filtering.
        
        Args:
            limit: Maximum number of logs to return
            backend_type: Filter by backend type (ldap, sql, etc.)
            backend_name: Filter by backend name
            success: Filter by success status (True/False)
            username: Filter by username (partial match)
            since: ISO timestamp - only return logs after this time
        
        Returns:
            List of log entries, newest first
        """
        with self._lock:
            logs = list(self._buffer)
        
        # Apply filters
        if backend_type:
            logs = [l for l in logs if l.get('backend_type') == backend_type]
        
        if backend_name:
            logs = [l for l in logs if l.get('backend_name') == backend_name]
        
        if success is not None:
            logs = [l for l in logs if l.get('success') == success]
        
        if username:
            logs = [l for l in logs if username.lower() in l.get('username', '').lower()]
        
        if since:
            logs = [l for l in logs if l.get('timestamp', '') >= since]
        
        # Return newest first, limited
        return logs[-limit:][::-1]
    
    def clear(self):
        """Clear all log entries."""
        with self._lock:
            self._buffer.clear()
            logger.info("Authentication log buffer cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get buffer statistics.
        
        Returns:
            Dictionary with stats (size, max_size, success_rate, etc.)
        """
        with self._lock:
            logs = list(self._buffer)
        
        if not logs:
            return {
                'size': 0,
                'max_size': self.max_size,
                'success_rate': 0.0,
                'total_successes': 0,
                'total_failures': 0
            }
        
        successes = sum(1 for l in logs if l.get('success'))
        failures = len(logs) - successes
        
        return {
            'size': len(logs),
            'max_size': self.max_size,
            'success_rate': (successes / len(logs) * 100) if logs else 0.0,
            'total_successes': successes,
            'total_failures': failures,
            'oldest_entry': logs[0].get('timestamp') if logs else None,
            'newest_entry': logs[-1].get('timestamp') if logs else None
        }


# Global instances for different auth systems
auth_provider_logs = AuthLogBuffer(max_size=1000)
radius_backend_logs = AuthLogBuffer(max_size=1000)
