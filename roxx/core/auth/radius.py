import logging
import socket

logger = logging.getLogger("roxx.auth.radius")

class RadiusProvider:
    """
    RADIUS Authentication Provider
    
    Uses pyrad library for RADIUS authentication.
    Install with: pip install pyrad
    """
    
    @staticmethod
    def get_config():
        """
        Get RADIUS configuration from database.
        
        Returns:
            dict with 'server', 'port', 'secret' keys, or None if not configured
        """
        try:
            from roxx.core.auth.config_db import ConfigManager
            provider = ConfigManager.get_active_provider('radius')
            if provider and provider.get('enabled'):
                return provider['config']
        except Exception as e:
            logger.warning(f"Could not load RADIUS config from database: {e}")
        
        return None
    
    @staticmethod
    def verify_credentials(username, password):
        """
        Verify credentials against RADIUS server.
        Uses database configuration.
        """
        config = RadiusProvider.get_config()
        
        if not config:
            logger.error("RADIUS Configuration missing")
            return False
        
        return RadiusProvider._verify_with_config(config, username, password)
    
    @staticmethod
    def test_connection(config, test_username, test_password):
        """
        Test RADIUS connection with provided configuration.
        Used for validating config before saving.
        """
        return RadiusProvider._verify_with_config(config, test_username, test_password)
    
    @staticmethod
    def _verify_with_config(config, username, password):
        """
        Internal method to verify credentials with given config.
        """
        try:
            from pyrad.client import Client
            from pyrad.dictionary import Dictionary
            from pyrad.packet import AccessRequest
            import os
            
            server = config.get('server')
            port = int(config.get('port', 1812))
            secret = config.get('secret')
            timeout = int(config.get('timeout', 5))
            
            if not server or not secret:
                logger.error("RADIUS config missing required fields")
                return False
            
            # Create a minimal RADIUS dictionary
            # pyrad requires a dictionary file, but we can create one in memory
            dict_content = """
# Minimal RADIUS dictionary
ATTRIBUTE   User-Name       1   string
ATTRIBUTE   User-Password   2   string
ATTRIBUTE   Reply-Message   18  string
"""
            dict_path = "/tmp/roxx_radius_dict.txt"
            with open(dict_path, 'w') as f:
                f.write(dict_content)
            
            # Create RADIUS client
            client = Client(
                server=server,
                authport=port,
                secret=secret.encode('utf-8'),
                dict=Dictionary(dict_path)
            )
            client.timeout = timeout
            
            # Create Access-Request packet
            req = client.CreateAuthPacket(code=AccessRequest)
            req["User-Name"] = username
            req["User-Password"] = req.PwCrypt(password)
            
            # Send to server
            reply = client.SendPacket(req)
            
            # Check response
            if reply.code == 2:  # Access-Accept
                logger.info(f"RADIUS authentication successful for {username}")
                return True
            else:
                logger.warning(f"RADIUS authentication failed for {username}")
                return False
                
        except ImportError:
            logger.error("pyrad library not installed. Install with: pip install pyrad")
            return False
        except socket.timeout:
            logger.error(f"RADIUS server {server}:{port} timeout")
            return False
        except Exception as e:
            logger.error(f"RADIUS Error: {e}")
            return False
