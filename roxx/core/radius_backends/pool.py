"""
Connection Pool for RADIUS Backend Resources

Provides pre-initialized connection pooling for LDAP and SQL backends
to reduce connection overhead under high-concurrency 802.1X loads.
"""

import logging
import time
from threading import Lock, Condition
from typing import Any, Optional, Callable
from collections import deque

logger = logging.getLogger("roxx.radius_backends.pool")


class ConnectionPool:
    """
    Generic connection pool for backend resources (LDAP, SQL, etc.).
    
    Features:
    - Pre-creates connections on init
    - Health checks on idle connections
    - Automatic reconnection on failure
    - Configurable pool size and timeout
    """

    def __init__(self,
                 create_func: Callable[[], Any],
                 close_func: Callable[[Any], None] = None,
                 health_check_func: Callable[[Any], bool] = None,
                 pool_size: int = 5,
                 timeout: float = 30.0,
                 max_idle_time: float = 300.0):
        """
        Initialize connection pool.
        
        Args:
            create_func: Callable that creates a new connection
            close_func: Callable that closes a connection (optional)
            health_check_func: Callable that checks if connection is alive (optional)
            pool_size: Maximum number of connections in pool
            timeout: Max seconds to wait for a connection
            max_idle_time: Seconds before idle connection is recycled
        """
        self.create_func = create_func
        self.close_func = close_func or (lambda c: None)
        self.health_check_func = health_check_func or (lambda c: True)
        self.pool_size = pool_size
        self.timeout = timeout
        self.max_idle_time = max_idle_time

        self._pool = deque()  # Available connections: (conn, last_used_time)
        self._in_use = 0
        self._lock = Lock()
        self._available = Condition(self._lock)

        self._total_created = 0
        self._total_recycled = 0
        self._total_errors = 0

        # Pre-create connections
        self._warmup()

    def _warmup(self):
        """Pre-create initial connections"""
        for _ in range(min(2, self.pool_size)):  # Pre-create up to 2
            try:
                conn = self.create_func()
                self._pool.append((conn, time.time()))
                self._total_created += 1
                logger.debug(f"[Pool] Pre-created connection ({self._total_created} total)")
            except Exception as e:
                logger.warning(f"[Pool] Warmup connection failed: {e}")
                self._total_errors += 1

    def acquire(self) -> Any:
        """
        Acquire a connection from the pool.
        
        Returns:
            A connection object
            
        Raises:
            TimeoutError: If no connection available within timeout
        """
        with self._lock:
            deadline = time.time() + self.timeout

            while True:
                # Try to get from pool
                while self._pool:
                    conn, last_used = self._pool.popleft()

                    # Check if too old
                    if time.time() - last_used > self.max_idle_time:
                        logger.debug("[Pool] Recycling idle connection")
                        self._safe_close(conn)
                        self._total_recycled += 1
                        continue

                    # Health check
                    try:
                        if self.health_check_func(conn):
                            self._in_use += 1
                            return conn
                    except Exception:
                        pass

                    # Failed health check
                    self._safe_close(conn)
                    self._total_recycled += 1
                    logger.debug("[Pool] Connection failed health check, recycled")

                # No available connections - create new if under limit
                if self._in_use < self.pool_size:
                    try:
                        conn = self.create_func()
                        self._total_created += 1
                        self._in_use += 1
                        logger.debug(f"[Pool] Created new connection ({self._in_use}/{self.pool_size} in use)")
                        return conn
                    except Exception as e:
                        self._total_errors += 1
                        logger.error(f"[Pool] Failed to create connection: {e}")
                        raise

                # At capacity - wait
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise TimeoutError(f"Connection pool exhausted ({self.pool_size} max)")

                logger.debug(f"[Pool] Waiting for connection ({remaining:.1f}s remaining)")
                self._available.wait(timeout=remaining)

    def release(self, conn: Any):
        """Return a connection to the pool"""
        with self._lock:
            self._in_use -= 1
            self._pool.append((conn, time.time()))
            self._available.notify()
            logger.debug(f"[Pool] Connection released ({self._in_use}/{self.pool_size} in use)")

    def _safe_close(self, conn: Any):
        """Safely close a connection"""
        try:
            self.close_func(conn)
        except Exception as e:
            logger.debug(f"[Pool] Error closing connection: {e}")

    def close_all(self):
        """Close all connections in the pool"""
        with self._lock:
            while self._pool:
                conn, _ = self._pool.popleft()
                self._safe_close(conn)
            logger.info("[Pool] All connections closed")

    def stats(self) -> dict:
        """Get pool statistics"""
        with self._lock:
            return {
                "pool_size": self.pool_size,
                "available": len(self._pool),
                "in_use": self._in_use,
                "total_created": self._total_created,
                "total_recycled": self._total_recycled,
                "total_errors": self._total_errors,
            }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close_all()


class PooledConnection:
    """
    Context manager for using a pooled connection.
    
    Usage:
        pool = ConnectionPool(create_func=...)
        with PooledConnection(pool) as conn:
            conn.do_something()
    """

    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.conn = None

    def __enter__(self):
        self.conn = self.pool.acquire()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn is not None:
            if exc_type is not None:
                # Connection may be in bad state after error
                self.pool._safe_close(self.conn)
                with self.pool._lock:
                    self.pool._in_use -= 1
                    self.pool._available.notify()
            else:
                self.pool.release(self.conn)
        return False
