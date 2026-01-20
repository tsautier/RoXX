"""
TOTP (Time-based One-Time Password) Authentication Module
Linux replacement for bin/totp.sh
"""

import os
import sys
import hmac
import hashlib
import struct
import time
import logging
from pathlib import Path
from typing import Optional


class TOTPAuthenticator:
    """
    TOTP generator and validator (RFC 6238)
    
    Compatible with Google Authenticator, Microsoft Authenticator, etc.
    """
    
    def __init__(self, secret: str, digits: int = 6, period: int = 30, algorithm: str = 'SHA1'):
        """
        Initialize the TOTP generator
        
        Args:
            secret: Shared secret key (base32)
            digits: Number of digits in the code (usually 6)
            period: Validity period in seconds (usually 30)
            algorithm: Hash algorithm ('SHA1', 'SHA256', 'SHA512')
        """
        self.secret = secret
        self.digits = digits
        self.period = period
        
        # Select hash algorithm
        hash_algorithms = {
            'SHA1': hashlib.sha1,
            'SHA256': hashlib.sha256,
            'SHA512': hashlib.sha512,
        }
        self.hash_algorithm = hash_algorithms.get(algorithm.upper(), hashlib.sha1)
        
        self.logger = logging.getLogger(__name__)

    def _base32_decode(self, secret: str) -> bytes:
        """Decode a base32 secret key"""
        import base64
        # Add padding if necessary
        missing_padding = len(secret) % 8
        if missing_padding:
            secret += '=' * (8 - missing_padding)
        return base64.b32decode(secret.upper())

    def _get_counter(self, timestamp: Optional[int] = None) -> int:
        """Calculate the counter based on timestamp"""
        if timestamp is None:
            timestamp = int(time.time())
        return timestamp // self.period

    def generate(self, timestamp: Optional[int] = None) -> str:
        """
        Generate a TOTP code
        
        Args:
            timestamp: Unix timestamp (None = now)
            
        Returns:
            N-digit TOTP code
        """
        counter = self._get_counter(timestamp)
        
        # Decode the secret key
        try:
            key = self._base32_decode(self.secret)
        except Exception as e:
            self.logger.error(f"Failed to decode secret: {e}")
            raise ValueError("Invalid secret key")
        
        # Convert counter to bytes (big-endian)
        counter_bytes = struct.pack('>Q', counter)
        
        # Calculate HMAC
        hmac_hash = hmac.new(key, counter_bytes, self.hash_algorithm).digest()
        
        # Dynamic extraction (RFC 4226)
        offset = hmac_hash[-1] & 0x0F
        code = struct.unpack('>I', hmac_hash[offset:offset+4])[0] & 0x7FFFFFFF
        
        # Truncate to desired number of digits
        code = code % (10 ** self.digits)
        
        # Format with leading zeros
        return str(code).zfill(self.digits)

    def verify(self, code: str, timestamp: Optional[int] = None, window: int = 1) -> bool:
        """
        Verify a TOTP code
        
        Args:
            code: TOTP code to verify
            timestamp: Unix timestamp (None = now)
            window: Tolerance window (number of periods before/after)
            
        Returns:
            True if code is valid, False otherwise
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        # Check current code and codes in tolerance window
        for offset in range(-window, window + 1):
            check_timestamp = timestamp + (offset * self.period)
            expected_code = self.generate(check_timestamp)
            
            if code == expected_code:
                self.logger.info(f"TOTP code verified (offset: {offset})")
                return True
        
        self.logger.warning("TOTP code verification failed")
        return False


def main():
    """
    Entry point for command-line usage
    Compatible with FreeRADIUS exec module
    """
    # Get environment variables (FreeRADIUS)
    username = os.environ.get('USER_NAME', '').strip('"')
    password = os.environ.get('USER_PASSWORD', '').strip('"')
    
    if not username:
        print("NOUSERNAME", end='')
        logging.warning("USER_NAME variable not found")
        sys.exit(1)
    
    if not password:
        print("NOPASSWORD", end='')
        logging.warning("USER_PASSWORD variable not found")
        sys.exit(1)
    
    # Load user's secret key
    # (Adapt according to your storage system)
    from roxx.utils.system import SystemManager
    
    config_dir = SystemManager.get_config_dir()
    secrets_file = config_dir / "totp_secrets.txt"
    
    if not secrets_file.exists():
        print("NOSECRETS", end='')
        logging.error(f"Secrets file not found: {secrets_file}")
        sys.exit(1)
    
    # Search for user's secret key
    secret = None
    try:
        with open(secrets_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(':')
                if len(parts) >= 2 and parts[0] == username:
                    secret = parts[1]
                    break
    except Exception as e:
        print("ERRORFILE", end='')
        logging.error(f"Error reading secrets file: {e}")
        sys.exit(1)
    
    if not secret:
        print("NOSECRET", end='')
        logging.warning(f"No secret found for user {username}")
        sys.exit(1)
    
    # Verify TOTP code
    try:
        authenticator = TOTPAuthenticator(secret=secret)
        
        if authenticator.verify(password, window=1):
            print("OK", end='')
            logging.info(f"TOTP authentication successful for {username}")
            sys.exit(0)
        else:
            print("INVALID", end='')
            logging.warning(f"TOTP authentication failed for {username}")
            sys.exit(1)
            
    except ValueError as e:
        print("INVALIDSECRET", end='')
        logging.error(f"Invalid secret for {username}: {e}")
        sys.exit(1)
    except Exception as e:
        print("ERROR", end='')
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s: %(message)s'
    )
    main()
