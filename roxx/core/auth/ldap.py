import logging
from ldap3 import Server, Connection, SIMPLE, SYNC, ALL

logger = logging.getLogger("roxx.auth.ldap")

class LdapProvider:
    """
    LDAP Authentication Provider
    """
    
    @staticmethod
    def get_config():
        """
        Get LDAP configuration from database or environment variables (fallback).
        
        Returns:
            dict with 'server' and 'bind_dn_format' keys, or None if not configured
        """
        # Try database first
        try:
            from roxx.core.auth.config_db import ConfigManager
            provider = ConfigManager.get_active_provider('ldap')
            if provider and provider.get('enabled'):
                return provider['config']
        except Exception as e:
            logger.warning(f"Could not load LDAP config from database: {e}")
        
        # Fallback to environment variables
        import os
        server_uri = os.getenv("ROXX_LDAP_SERVER")
        bind_dn_fmt = os.getenv("ROXX_LDAP_BIND_DN_FMT")
        
        if server_uri and bind_dn_fmt:
            return {
                'server': server_uri,
                'bind_dn_format': bind_dn_fmt
            }
        
        return None
    
    @staticmethod
    def verify_credentials(username, password):
        """
        Verify credentials against LDAP.
        Uses database configuration or environment variables as fallback.
        """
        config = LdapProvider.get_config()
        
        if not config:
            logger.error("LDAP Configuration missing (no database config or env vars)")
            return False
        
        return LdapProvider._verify_with_config(config, username, password)
    
    @staticmethod
    def test_connection(config, test_username, test_password):
        """
        Test LDAP connection with provided configuration.
        Used for validating config before saving.
        """
        return LdapProvider._verify_with_config(config, test_username, test_password)
    
    @staticmethod
    def _verify_with_config(config, username, password):
        """
        Internal method to verify credentials with given config.
        """
        server_uri = config.get('server')
        bind_dn_fmt = config.get('bind_dn_format')
        use_tls = config.get('use_tls', False)
        
        if not server_uri or not bind_dn_fmt:
            logger.error("LDAP config missing required fields")
            return False
        
        # Format Bind DN
        if "{}" in bind_dn_fmt:
            user_dn = bind_dn_fmt.format(username)
        else:
            user_dn = bind_dn_fmt.replace("%u", username)
        
        try:
            from ldap3 import Tls
            import ssl
            
            # Configure TLS if requested
            tls_config = None
            if use_tls:
                # Create TLS configuration with certificate validation
                # For production, you might want to add certificate verification
                tls_config = Tls(validate=ssl.CERT_NONE)  # Use CERT_REQUIRED for production with proper certs
            
            # Create server with optional TLS
            server = Server(server_uri, get_info=ALL, tls=tls_config)
            
            # Create connection
            conn = Connection(server, user=user_dn, password=password, authentication=SIMPLE, client_strategy=SYNC)
            
            # If using ldap:// with TLS, call start_tls()
            if use_tls and server_uri.startswith('ldap://'):
                if not conn.start_tls():
                    logger.error(f"Failed to start TLS for {username}")
                    return False
            
            # Attempt bind
            if conn.bind():
                logger.info(f"LDAP Bind successful for {username}")
                conn.unbind()
                return True
            else:
                logger.warning(f"LDAP Bind failed for {username}: {conn.result}")
                return False
                
        except Exception as e:
            logger.error(f"LDAP Error: {e}")
            return False

