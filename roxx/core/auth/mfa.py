"""
Multi-Factor Authentication (MFA) Manager
Handles TOTP generation, verification, and backup codes
"""

import pyotp
import qrcode
import secrets
import hashlib
import io
import base64
from datetime import datetime
from typing import Tuple, List, Optional


class MFAManager:
    """Manage TOTP-based MFA for users"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret (base32 encoded)"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_totp_uri(username: str, secret: str, issuer: str = "RoXX") -> str:
        """
        Generate TOTP URI for QR code
        
        Args:
            username: User's username
            secret: TOTP secret
            issuer: Application name (default: RoXX)
            
        Returns:
            TOTP URI string
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=username,
            issuer_name=issuer
        )
    
    @staticmethod
    def generate_qr_code(totp_uri: str) -> str:
        """
        Generate QR code image as base64 data URL
        
        Args:
            totp_uri: TOTP URI from generate_totp_uri()
            
        Returns:
            Base64 encoded PNG image data URL
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 data URL
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def verify_totp(secret: str, token: str, valid_window: int = 1) -> bool:
        """
        Verify TOTP token
        
        Args:
            secret: User's TOTP secret
            token: 6-digit TOTP token from authenticator
            valid_window: Number of time windows to check (default: 1 = ±30 seconds)
            
        Returns:
            True if token is valid, False otherwise
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=valid_window)
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> Tuple[List[str], List[str]]:
        """
        Generate backup codes for account recovery
        
        Args:
            count: Number of backup codes to generate (default: 10)
            
        Returns:
            Tuple of (plain_codes, hashed_codes)
        """
        plain_codes = []
        hashed_codes = []
        
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()  # 8 hex chars
            plain_codes.append(code)
            
            # Hash the code for storage (SHA-256)
            hashed = hashlib.sha256(code.encode()).hexdigest()
            hashed_codes.append(hashed)
        
        return plain_codes, hashed_codes
    
    @staticmethod
    def verify_backup_code(code: str, hashed_codes: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Verify backup code and return the matched hash
        
        Args:
            code: Plain backup code from user
            hashed_codes: List of hashed backup codes
            
        Returns:
            Tuple of (is_valid, matched_hash)
        """
        code_hash = hashlib.sha256(code.upper().encode()).hexdigest()
        
        if code_hash in hashed_codes:
            return True, code_hash
        return False, None
    
    @staticmethod
    def get_time_remaining() -> int:
        """
        Get seconds remaining until next TOTP token
        
        Returns:
            Seconds until token expires
        """
        totp = pyotp.TOTP("dummy")  # Secret doesn't matter for time calc
        current_time = datetime.now().timestamp()
        time_step = 30  # TOTP uses 30-second intervals
        return int(time_step - (current_time % time_step))


# Example usage
if __name__ == "__main__":
    # Generate secret
    secret = MFAManager.generate_secret()
    print(f"Secret: {secret}")
    
    # Generate TOTP URI
    uri = MFAManager.generate_totp_uri("testuser", secret)
    print(f"URI: {uri}")
    
    # Generate QR code
    qr_data = MFAManager.generate_qr_code(uri)
    print(f"QR Code Data URL: {qr_data[:50]}...")
    
    # Generate current token (for testing)
    totp = pyotp.TOTP(secret)
    token = totp.now()
    print(f"Current Token: {token}")
    
    # Verify token
    is_valid = MFAManager.verify_totp(secret, token)
    print(f"Token Valid: {is_valid}")
    
    # Generate backup codes
    plain, hashed = MFAManager.generate_backup_codes(5)
    print(f"Backup Codes: {plain}")
    
    # Verify backup code
    valid, matched = MFAManager.verify_backup_code(plain[0], hashed)
    print(f"Backup Code Valid: {valid}")
