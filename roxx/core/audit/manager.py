from roxx.core.audit.db import AuditDatabase
import logging
import logging.handlers
import os

# Configure Syslog if enabled
syslog_host = os.getenv("ROXX_SYSLOG_HOST")
syslog_port = int(os.getenv("ROXX_SYSLOG_PORT", 514))
syslog_enabled = bool(syslog_host)

syslog_logger = logging.getLogger("roxx.audit.syslog")
syslog_logger.setLevel(logging.INFO)

if syslog_enabled:
    try:
        handler = logging.handlers.SysLogHandler(address=(syslog_host, syslog_port))
        formatter = logging.Formatter('%(name)s: [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        syslog_logger.addHandler(handler)
        print(f"[AUDIT] Syslog enabled sending to {syslog_host}:{syslog_port}")
    except Exception as e:
        print(f"[AUDIT] Failed to configure syslog: {e}")

class AuditManager:
    @staticmethod
    def log(request, action: str, severity: str = "INFO", details: dict = None, username: str = None):
        """
        Helper to log events from FastAPI requests.
         Automatically extracts IP and Username (from session) if not provided.
        """
        try:
            # Extract IP
            ip_address = "unknown"
            if request and request.client:
                ip_address = request.client.host
            
            # Extract Username if not explicitly provided
            if not username and request:
                # Try to get from session or user object if available
                # This depends on how auth is handled in the endpoint
                if hasattr(request, "session"):
                     # Try common session keys
                     username = request.session.get("username") or request.session.get("user")
                
            final_username = username if username else "anonymous"
            
            # 1. Write to Local DB
            AuditDatabase.log_event(
                username=final_username,
                ip_address=ip_address,
                action=action,
                severity=severity,
                details=details
            )
            
            # 2. Send to Syslog (if enabled)
            if syslog_enabled:
                msg = f"User={final_username} IP={ip_address} Action={action} Details={details}"
                if severity == "ERROR":
                    syslog_logger.error(msg)
                elif severity == "WARNING":
                    syslog_logger.warning(msg)
                else:
                    syslog_logger.info(msg)
                    
        except Exception as e:
            # Fallback print to ensure we don't crash the app if logging fails
            print(f"[AUDIT ERROR] Failed to log: {e}")
