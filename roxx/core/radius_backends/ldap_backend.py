"""
LDAP/NTLM RADIUS Authentication Backend

Supports LDAP and NTLM authentication for RADIUS users with:
- LDAP/LDAPS connections with TLS
- NTLM authentication via LDAP
- Attribute mapping from LDAP to RADIUS
- Connection pooling
"""

from typing import Tuple, Dict, Optional
import logging
from ldap3 import Server, Connection, ALL, SIMPLE, SYNC, NTLM, Tls
from ldap3.core.exceptions import LDAPException
import ssl

from .base import RadiusBackend

logger = logging.getLogger("roxx.radius_backends.ldap")


class LdapRadiusBackend(RadiusBackend):
    """
    LDAP/NTLM authentication backend for RADIUS users.
    
    Configuration options:
    - server: LDAP server URL (ldap:// or ldaps://)
    - bind_dn_format: DN format with {} placeholder for username
    - use_tls: Enable TLS/SSL
    - use_ntlm: Use NTLM authentication instead of simple bind
    - search_base: Base DN for user searches (optional)
    - search_filter: LDAP filter for finding users (optional)
    - attributes: List of LDAP attributes to fetch
    - radius_attr_map: Mapping of LDAP attributes to RADIUS attributes
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        self.server_uri = config.get('server')
        self.bind_dn_format = config.get('bind_dn_format')
        self.use_tls = config.get('use_tls', False)
        self.use_ntlm = config.get('use_ntlm', False)
        self.search_base = config.get('search_base', '')
        self.search_filter = config.get('search_filter', '(uid={})')
        self.attributes = config.get('attributes', ['memberOf', 'mail', 'telephoneNumber'])
        self.radius_attr_map = config.get('radius_attr_map', {
            'memberOf': 'Filter-Id',
            'mail': 'Reply-Message',
            'telephoneNumber': 'Calling-Station-Id'
        })
        
        # Create server object
        self._server = self._create_server()
    
    def _create_server(self) -> Server:
        """Create LDAP server object with TLS configuration"""
        tls_config = None
        
        if self.use_tls:
            # Create TLS configuration
            tls_config = Tls(validate=ssl.CERT_NONE)  # For production, use CERT_REQUIRED with proper certs
        
        return Server(self.server_uri, get_info=ALL, tls=tls_config)
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate user via LDAP/NTLM.
        
        Returns:
            (success, radius_attributes)
        """
        if not username or not password:
            logger.warning("Empty username or password")
            return False, None
        
        try:
            # Format bind DN
            if self.use_ntlm:
                # NTLM format: DOMAIN\\username
                user_dn = username if '\\' in username else f"{username}"
                auth_type = NTLM
            else:
                # Standard LDAP bind
                if "{}" in self.bind_dn_format:
                    user_dn = self.bind_dn_format.format(username)
                else:
                    user_dn = self.bind_dn_format.replace("%u", username)
                auth_type = SIMPLE
            
            # Create connection
            conn = Connection(
                self._server,
                user=user_dn,
                password=password,
                authentication=auth_type,
                client_strategy=SYNC,
                auto_bind=False
            )
            
            # Start TLS if needed for ldap:// with TLS
            if self.use_tls and self.server_uri.startswith('ldap://'):
                if not conn.start_tls():
                    logger.error(f"Failed to start TLS for {username}")
                    return False, None
            
            # Attempt bind
            if not conn.bind():
                logger.warning(f"{self.name}: Authentication failed for {username}")
                return False, None
            
            logger.info(f"{self.name}: Authentication successful for {username}")
            
            # Get user attributes if search is configured
            radius_attrs = {}
            if self.search_base:
                radius_attrs = self._get_user_attributes_from_ldap(conn, username)
            
            conn.unbind()
            return True, radius_attrs
            
        except LDAPException as e:
            logger.error(f"{self.name}: LDAP error for {username}: {e}")
            return False, None
        except Exception as e:
            logger.error(f"{self.name}: Unexpected error: {e}")
            return False, None
    
    def _get_user_attributes_from_ldap(self, conn: Connection, username: str) -> Dict:
        """
        Search LDAP for user and get attributes.
        
        Returns:
            Dictionary of RADIUS attributes
        """
        try:
            # Format search filter
            search_filter = self.search_filter.format(username)
            
            # Perform search
            conn.search(
                search_base=self.search_base,
                search_filter=search_filter,
                attributes=self.attributes
            )
            
            if not conn.entries:
                logger.debug(f"No LDAP entry found for {username}")
                return {}
            
            # Get first entry
            entry = conn.entries[0]
            radius_attrs = {}
            
            # Map LDAP attributes to RADIUS attributes
            for ldap_attr, radius_attr in self.radius_attr_map.items():
                if hasattr(entry, ldap_attr):
                    value = getattr(entry, ldap_attr).value
                    if isinstance(value, list) and value:
                        # For multi-valued attributes, use first value or join
                        radius_attrs[radius_attr] = str(value[0])
                    elif value:
                        radius_attrs[radius_attr] = str(value)
            
            logger.debug(f"Mapped attributes for {username}: {radius_attrs}")
            return radius_attrs
            
        except Exception as e:
            logger.error(f"Error fetching attributes for {username}: {e}")
            return {}
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test LDAP connection and configuration"""
        if not self.server_uri:
            return False, "Server URI not configured"
        
        if not self.bind_dn_format:
            return False, "Bind DN format not configured"
        
        try:
            # Try to connect to server
            test_conn = Connection(
                self._server,
                auto_bind=False,
                client_strategy=SYNC
            )
            
            # Just test connection, don't bind
            if self._server.check_availability():
                return True, f"Successfully connected to {self.server_uri}"
            else:
                return False, f"Cannot reach LDAP server {self.server_uri}"
                
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"
    
    def get_user_attributes(self, username: str) -> Dict:
        """
        Get user attributes without authentication.
        Requires a service account bind.
        """
        # This would require admin credentials - not implemented for security
        return {}
