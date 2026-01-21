"""
CSRF Protection for RoXX
Protects against Cross-Site Request Forgery attacks
"""

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import secrets
from typing import Optional

# Secret key for CSRF tokens (in production, load from environment)
CSRF_SECRET_KEY = secrets.token_hex(32)

# Token expiration time (1 hour)
CSRF_TOKEN_EXPIRATION = 3600

# Initialize serializer
serializer = URLSafeTimedSerializer(CSRF_SECRET_KEY)

def generate_csrf_token() -> str:
    """Generate a new CSRF token"""
    random_data = secrets.token_urlsafe(32)
    return serializer.dumps(random_data, salt='csrf-token')

def validate_csrf_token(token: str, max_age: int = CSRF_TOKEN_EXPIRATION) -> bool:
    """Validate a CSRF token
    
    Args:
        token: The CSRF token to validate
        max_age: Maximum age of token in seconds (default: 1 hour)
        
    Returns:
        True if token is valid, False otherwise
    """
    if not token:
        return False
        
    try:
        serializer.loads(token, salt='csrf-token', max_age=max_age)
        return True
    except (BadSignature, SignatureExpired):
        return False

def get_csrf_token_from_request(request) -> Optional[str]:
    """Extract CSRF token from request
    
    Checks in order:
    1. Form data (_csrf_token)
    2. Headers (X-CSRF-Token)
    3. Query parameters (_csrf_token)
    """
    # Check form data
    if hasattr(request, 'form'):
        token = request.form.get('_csrf_token')
        if token:
            return token
    
    # Check headers
    token = request.headers.get('X-CSRF-Token')
    if token:
        return token
    
    # Check query parameters
    if hasattr(request, 'query_params'):
        token = request.query_params.get('_csrf_token')
        if token:
            return token
            
    return None
