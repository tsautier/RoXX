"""
RADIUS Backend Manager

Manages multiple authentication backends with priority-based fallback.
Includes caching for performance optimization.
"""

from typing import Tuple, Optional, Dict, List
import logging

from .base import RadiusBackend
from .ldap_backend import LdapRadiusBackend
from .sql_backend import SqlRadiusBackend
from .file_backend import FileRadiusBackend
from .cache import AuthCache
from .config_db import RadiusBackendDB

logger = logging.getLogger("roxx.radius_backends.manager")


class RadiusBackendManager:
    """
    Manager for RADIUS authentication backends.
    
    Handles:
    - Loading backends from database
    - Priority-based authentication with fallback
    - Authentication result caching
    - Backend health monitoring
    """
    
    # Backend class mapping
    BACKEND_CLASSES = {
        'ldap': LdapRadiusBackend,
        'ntlm': LdapRadiusBackend,  # NTLM uses LDAP backend with use_ntlm flag
        'sql': SqlRadiusBackend,
        'file': FileRadiusBackend
    }
    
    def __init__(self, cache_ttl: int = 300, cache_size: int = 1000):
        """
        Initialize backend manager.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
            cache_size: Maximum cache entries (default: 1000)
        """
        self.backends: List[RadiusBackend] = []
        self.cache = AuthCache(ttl=cache_ttl, max_size=cache_size)
        self._load_backends()
    
    def _load_backends(self):
        """Load and instantiate backends from database configuration"""
        try:
            # Initialize database if needed
            RadiusBackendDB.init()
            
            # Get enabled backends ordered by priority
            backend_configs = RadiusBackendDB.list_backends(enabled_only=True)
            
            self.backends = []
            for config in backend_configs:
                backend_type = config['backend_type']
                backend_config = config['config']
                backend_config['name'] = config['name']
                backend_config['enabled'] = config['enabled']
                
                # Special handling for NTLM
                if backend_type == 'ntlm':
                    backend_config['use_ntlm'] = True
                    backend_type = 'ldap'  # Use LDAP backend class
                
                backend_class = self.BACKEND_CLASSES.get(backend_type)
                if backend_class:
                    try:
                        backend = backend_class(backend_config)
                        self.backends.append(backend)
                        logger.info(f"Loaded backend: {backend.get_name()} ({backend_type})")
                    except Exception as e:
                        logger.error(f"Failed to initialize {backend_type} backend: {e}")
                else:
                    logger.warning(f"Unknown backend type: {backend_type}")
            
            logger.info(f"Loaded {len(self.backends)} RADIUS backends")
            
        except Exception as e:
            logger.error(f"Error loading backends: {e}")
            self.backends = []
    
    def reload_backends(self):
        """Reload backends from database (call after configuration changes)"""
        logger.info("Reloading RADIUS backends...")
        self._load_backends()
        self.cache.clear()  # Clear cache on reload
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate user against configured backends.
        
        Supports MFA: If user has MFA enabled, password should be: password+TOTP
        Example: "MyPassword123456" where 123456 is the 6-digit TOTP code
        
        Tries backends in priority order (lower priority number first).
        Uses cache for performance optimization.
        
        Args:
            username: Username to authenticate
            password: Password to verify (may include TOTP appended)
            
        Returns:
            (success: bool, radius_attributes: dict or None)
        """
        if not username or not password:
            logger.warning("Empty username or password")
            return False, None
        
        # Check if user has MFA enabled
        from roxx.core.auth.mfa_db import MFADatabase
        from roxx.core.auth.mfa import MFAManager
        
        mfa_enabled = MFADatabase.is_mfa_enabled(username)
        actual_password = password
        totp_verified = False
        
        if mfa_enabled:
            # MFA enabled - expect password+TOTP (last 6 digits)
            if len(password) > 6:
                base_password = password[:-6]  # All except last 6 chars
                totp_token = password[-6:]      # Last 6 chars
                
                # Verify TOTP token
                settings = MFADatabase.get_mfa_settings(username)
                if settings and settings.get('totp_secret'):
                    if MFAManager.verify_totp(settings['totp_secret'], totp_token):
                        actual_password = base_password
                        totp_verified = True
                        logger.info(f"TOTP verified for {username}")
                    else:
                        logger.warning(f"Invalid TOTP for {username}")
                        return False, None
                else:
                    logger.error(f"MFA enabled but no secret found for {username}")
                    return False, None
            else:
                logger.warning(f"MFA enabled for {username} but password too short for TOTP")
                return False, None
        
        # 1. Check cache first (use base password if MFA)
        cached_result = self.cache.get(username, actual_password)
        if cached_result is not None and (not mfa_enabled or totp_verified):
            logger.info(f"Authentication from cache for {username}")
            MFADatabase.update_last_used(username) if mfa_enabled else None
            return cached_result
        
        # 2. Try each backend in priority order
        if not self.backends:
            logger.warning("No backends configured!")
            return False, None
        
        for backend in self.backends:
            if not backend.is_enabled():
                continue
            
            try:
                logger.debug(f"Trying backend: {backend.get_name()}")
                success, attributes = backend.authenticate(username, actual_password)
                
                if success:
                    logger.info(f"Authentication successful via {backend.get_name()} for {username}")
                    
                    # Update MFA last used if applicable
                    if mfa_enabled and totp_verified:
                        MFADatabase.update_last_used(username)
                    
                    # Cache successful authentication (with base password)
                    self.cache.set(username, actual_password, attributes or {})
                    
                    return True, attributes
                else:
                    # Try next backend
                    logger.debug(f"Authentication failed via {backend.get_name()}, trying next...")
                    continue
                    
            except Exception as e:
                logger.error(f"Backend {backend.get_name()} error: {e}")
                # Continue to next backend on error
                continue
        
        # All backends failed
        logger.warning(f"Authentication failed for {username} (all backends exhausted)")
        return False, None

    
    def test_backend(self, backend_type: str, config: dict, test_username: str, test_password: str) -> Tuple[bool, str]:
        """
        Test backend configuration without saving.
        
        Args:
            backend_type: Type of backend ('ldap', 'sql', 'file')
            config: Backend configuration dict
            test_username: Test username
            test_password: Test password
            
        Returns:
            (success, message)
        """
        try:
            # Special handling for NTLM
            if backend_type == 'ntlm':
                config['use_ntlm'] = True
                backend_type = 'ldap'
            
            backend_class = self.BACKEND_CLASSES.get(backend_type)
            if not backend_class:
                return False, f"Unknown backend type: {backend_type}"
            
            # Create temporary backend instance
            config['name'] = 'Test Backend'
            backend = backend_class(config)
            
            # Test connection
            conn_success, conn_msg = backend.test_connection()
            if not conn_success:
                return False, f"Connection test failed: {conn_msg}"
            
            # Test authentication if credentials provided
            if test_username and test_password:
                auth_success, _ = backend.authenticate(test_username, test_password)
                if auth_success:
                    return True, "Backend configuration and authentication test successful"
                else:
                    return False, f"Connection OK but authentication failed for {test_username}"
            else:
                return True, f"Backend connection test successful: {conn_msg}"
                
        except Exception as e:
            return False, f"Backend test error: {str(e)}"
    
    def get_stats(self) -> dict:
        """Get manager statistics"""
        return {
            'backends_count': len(self.backends),
            'backends': [
                {
                    'name': b.get_name(),
                    'type': b.__class__.__name__,
                    'enabled': b.is_enabled()
                }
                for b in self.backends
            ],
            'cache': self.cache.stats()
        }


# Global instance for FreeRADIUS integration
_global_manager = None


def get_manager() -> RadiusBackendManager:
    """Get global manager instance (singleton)"""
    global _global_manager
    if _global_manager is None:
        _global_manager = RadiusBackendManager()
    return _global_manager


def reload_manager():
    """Reload global manager"""
    global _global_manager
    if _global_manager:
        _global_manager.reload_backends()
    else:
        _global_manager = RadiusBackendManager()
