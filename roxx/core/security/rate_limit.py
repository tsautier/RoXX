"""
Rate Limiting Configuration for RoXX
Protects authentication and API endpoints from brute force and DoS attacks
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
RATE_LIMITS = {
    # Authentication endpoints - strict limits
    "login": "5/minute",           # 5 login attempts per minute
    "totp_verify": "10/minute",    # 10 TOTP verifications per minute
    "webauthn": "10/minute",       # 10 WebAuthn attempts per minute
    
    # API endpoints - moderate limits
    "api_write": "30/minute",      #30 write operations per minute
    "api_read": "60/minute",       # 60 read operations per minute
    
    # SAML/Auth providers - moderate limits
    "saml_acs": "20/minute",       # 20 SAML assertions per minute
    "auth_provider": "30/minute",  # 30 provider requests per minute
    
    # General - relaxed limits
    "general": "100/minute",       # 100 general requests per minute
}

def get_rate_limit(endpoint_type: str) -> str:
    """Get rate limit for a specific endpoint type"""
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["general"])
