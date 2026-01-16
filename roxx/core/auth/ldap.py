"""
Generic LDAP Authentication Module (RFC 4510)
Supports Active Directory, OpenLDAP, and other standard directories.
"""

from typing import Optional, Dict, Any
from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError
from loguru import logger


class LDAPAuthenticator:
    """Generic LDAP Authentication Provider"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LDAP Authenticator
        
        Args:
            config: Configuration dictionary containing:
                - server: LDAP server hostname/IP
                - port: LDAP port (default 389/636)
                - use_ssl: Boolean for LDAPS
                - use_start_tls: Boolean for StartTLS
                - base_dn: Base DN for user search
                - bind_dn: DN to use for initial bind (optional)
                - bind_password: Password for bind DN (optional)
                - user_search_filter: Custom filter (default: (uid={user}))
        """
        self.server_host = config.get('server')
        self.port = int(config.get('port', 636 if config.get('use_ssl') else 389))
        self.use_ssl = config.get('use_ssl', False)
        self.use_start_tls = config.get('use_start_tls', False)
        
        self.base_dn = config.get('base_dn')
        self.bind_dn = config.get('bind_dn')
        self.bind_password = config.get('bind_password')
        self.user_search_filter = config.get('user_search_filter', '(uid={user})')
        
        self.logger = logger.bind(module="auth.ldap")

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate a user against LDAP
        
        Args:
            username: Username provided by RADIUS
            password: Password provided by RADIUS
            
        Returns:
            True if authentication successful, False otherwise
        """
        if not username or not password:
            return False

        try:
            # 1. Connect to server
            server = Server(self.server_host, port=self.port, use_ssl=self.use_ssl, get_info=ALL)
            
            # 2. Strategy: Search & Bind (recommended) or Direct Bind
            if self.bind_dn and self.bind_password:
                return self._search_and_bind(server, username, password)
            else:
                return self._simple_bind(server, username, password)

        except LDAPException as e:
            self.logger.error(f"LDAP Error: {e}")
            return False
        except Exception as e:
            self.logger.exception(f"Unexpected error during LDAP auth: {e}")
            return False

    def _simple_bind(self, server: Server, username: str, password: str) -> bool:
        """Strategy 1: Direct Bind (username is DN)"""
        # Note: This usually requires the username to be a full DN, unless AD is used
        user_dn = username
        
        # If generic AD style user@domain
        # user_dn = f"{username}@{self.domain}" 

        try:
            conn = Connection(server, user=user_dn, password=password, auto_bind=True)
            self.logger.info(f"User {username} authenticated successfully (Direct Bind)")
            conn.unbind()
            return True
        except LDAPBindError:
            self.logger.warning(f"Authentication failed for user {username}")
            return False

    def _search_and_bind(self, server: Server, username: str, password: str) -> bool:
        """Strategy 2: Search for user DN, then Bind as user"""
        
        # A. Bind as Service Account
        try:
            conn = Connection(server, user=self.bind_dn, password=self.bind_password, auto_bind=True)
            if self.use_start_tls:
                conn.start_tls()
        except LDAPBindError:
            self.logger.error("Failed to bind with Service Account credentials")
            return False

        # B. Search for user DN
        search_filter = self.user_search_filter.format(user=username)
        conn.search(self.base_dn, search_filter, search_scope=SUBTREE, attributes=['dn'])
        
        if len(conn.entries) != 1:
            self.logger.warning(f"User search failed: Found {len(conn.entries)} entries for {username}")
            conn.unbind()
            return False
        
        user_dn = conn.entries[0].entry_dn
        conn.unbind()

        # C. Re-bind as User to verify password
        try:
            user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
            self.logger.info(f"User {username} authenticated successfully (DN: {user_dn})")
            user_conn.unbind()
            return True
        except LDAPBindError:
            self.logger.warning(f"Authentication failed for user {username}")
            return False
