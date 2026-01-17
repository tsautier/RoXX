import logging
from ldap3 import Server, Connection, SIMPLE, SYNC, ALL

logger = logging.getLogger("roxx.auth.ldap")

class LdapProvider:
    """
    LDAP Authentication Provider
    """
    
    @staticmethod
    def verify_credentials(username, password):
        """
        Verify credentials against LDAP.
        Requires configuration:
        - ROXX_LDAP_SERVER: ldap://hostname:389
        - ROXX_LDAP_BIND_DN_FMT: "uid={},ou=users,dc=example,dc=com" or "DOMAIN\\{}"
        """
        import os
        
        server_uri = os.getenv("ROXX_LDAP_SERVER")
        bind_dn_fmt = os.getenv("ROXX_LDAP_BIND_DN_FMT")
        
        if not server_uri or not bind_dn_fmt:
            logger.error("LDAP Configuration missing (ROXX_LDAP_SERVER, ROXX_LDAP_BIND_DN_FMT)")
            return False
            
        # Format Bind DN
        # If bind_dn_fmt contains {}, format it with username
        if "{}" in bind_dn_fmt:
            user_dn = bind_dn_fmt.format(username)
        else:
            # Assume it's a domain/search base scenario - simpler implementation for now:
            # Just try direct bind with constructed DN
             user_dn = bind_dn_fmt.replace("%u", username)
             
        try:
            server = Server(server_uri, get_info=ALL)
            conn = Connection(server, user=user_dn, password=password, authentication=SIMPLE, client_strategy=SYNC)
            
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
