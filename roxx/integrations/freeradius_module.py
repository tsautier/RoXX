"""
FreeRADIUS rlm_python Module

This module is loaded directly by FreeRADIUS as a Python module.
It provides authentication using RoXX RADIUS backends.

Installation:
1. Copy this file to FreeRADIUS Python modules directory
2. Configure in FreeRADIUS sites-enabled:
   
   python {
       mod_path = "/path/to/roxx"
       module = "roxx.integrations.freeradius_module"
       func_authorize = authorize
       func_authenticate = authenticate
       func_post_auth = post_auth
   }

3. In your site config:
   authorize {
       ...
       python
   }
   
   authenticate {
       ...
       python
   }
"""

import radiusd
import sys
import os
import logging

# Setup logging for FreeRADIUS
logger = logging.getLogger("roxx.freeradius")
logger.setLevel(logging.INFO)

# Add RoXX to path if needed
ROXX_PATH = os.environ.get('ROXX_PATH', '/opt/roxx')
if ROXX_PATH not in sys.path:
    sys.path.insert(0, ROXX_PATH)

# Import RoXX backend manager
try:
    from roxx.core.radius_backends.manager import get_manager
    from roxx.core.radius_backends.config_db import RadiusBackendDB
    
    # Initialize database
    RadiusBackendDB.init()
    
    # Get global manager instance
    manager = get_manager()
    logger.info("RoXX RADIUS backends initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RoXX backends: {e}")
    manager = None


def log(level, msg):
    """Log message to FreeRADIUS"""
    radiusd.radlog(level, f"[RoXX] {msg}")


def authorize(p):
    """
    Authorization phase - called before authentication.
    
    Args:
        p: Packet tuple containing RADIUS attributes
    
    Returns:
        radiusd.RLM_MODULE_* constant
    """
    log(radiusd.L_INFO, "authorize() called")
    
    # Extract username from packet
    username = None
    for item in p:
        if item[0] == 'User-Name':
            username = item[1]
            break
    
    if username:
        log(radiusd.L_INFO, f"Authorizing user: {username}")
    
    # Always return OK to proceed to authentication
    return radiusd.RLM_MODULE_OK


def authenticate(p):
    """
    Authentication phase - actual credential verification.
    
    Args:
        p: Packet tuple containing RADIUS attributes
    
    Returns:
        (radiusd.RLM_MODULE_*, reply_tuple, config_tuple)
    """
    log(radiusd.L_INFO, "authenticate() called")
    
    # Check if manager is initialized
    if manager is None:
        log(radiusd.L_ERR, "Backend manager not initialized")
        return radiusd.RLM_MODULE_FAIL
    
    # Extract username and password from packet
    username = None
    password = None
    
    for item in p:
        if item[0] == 'User-Name':
            username = item[1]
        elif item[0] == 'User-Password':
            password = item[1]
    
    if not username or not password:
        log(radiusd.L_ERR, "Missing username or password")
        return radiusd.RLM_MODULE_REJECT
    
    log(radiusd.L_INFO, f"Authenticating user: {username}")
    
    try:
        # Authenticate using backend manager
        success, attributes = manager.authenticate(username, password)
        
        if success:
            log(radiusd.L_INFO, f"Authentication successful for {username}")
            
            # Build reply tuple from attributes
            reply_tuple = ()
            if attributes:
                for attr_name, attr_value in attributes.items():
                    reply_tuple += ((attr_name, attr_value),)
            
            # Return success with attributes
            return (radiusd.RLM_MODULE_OK, reply_tuple, ())
        else:
            log(radiusd.L_AUTH, f"Authentication failed for {username}")
            return radiusd.RLM_MODULE_REJECT
            
    except Exception as e:
        log(radiusd.L_ERR, f"Authentication error: {e}")
        return radiusd.RLM_MODULE_FAIL


def post_auth(p):
    """
    Post-authentication phase - called after successful authentication.
    
    Args:
        p: Packet tuple containing RADIUS attributes
    
    Returns:
        radiusd.RLM_MODULE_* constant
    """
    log(radiusd.L_INFO, "post_auth() called")
    
    # Extract username
    username = None
    for item in p:
        if item[0] == 'User-Name':
            username = item[1]
            break
    
    if username:
        log(radiusd.L_INFO, f"Post-auth for {username}")
    
    return radiusd.RLM_MODULE_OK


def detach(p):
    """
    Called when FreeRADIUS shuts down.
    
    Args:
        p: Context (unused)
    
    Returns:
        radiusd.RLM_MODULE_OK
    """
    log(radiusd.L_INFO, "Detaching RoXX module")
    return radiusd.RLM_MODULE_OK


# Module metadata
def instantiate(p):
    """
    Called when module is loaded.
    
    Args:
        p: Configuration (unused)
    
    Returns:
        radiusd.RLM_MODULE_OK or radiusd.RLM_MODULE_FAIL
    """
    log(radiusd.L_INFO, "Instantiating RoXX RADIUS module")
    
    if manager is None:
        log(radiusd.L_ERR, "Failed to initialize backend manager")
        return radiusd.RLM_MODULE_FAIL
    
    # Get manager stats
    stats = manager.get_stats()
    log(radiusd.L_INFO, f"Loaded {stats['backends_count']} RADIUS backends")
    
    for backend_info in stats['backends']:
        log(radiusd.L_INFO, f"  - {backend_info['name']} ({backend_info['type']}): {'enabled' if backend_info['enabled'] else 'disabled'}")
    
    return radiusd.RLM_MODULE_OK
