"""
Unit tests for MFA Manager (TOTP, QR codes, backup codes)
"""

import pytest
import pyotp
import re
from roxx.core.auth.mfa import MFAManager


class TestMFAManager:
    """Test MFA Manager functionality"""
    
    def test_generate_secret(self):
        """Test TOTP secret generation"""
        secret = MFAManager.generate_secret()
        
        # Should be base32 encoded string
        assert isinstance(secret, str)
        assert len(secret) == 32
        assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567' for c in secret)
    
    def test_generate_totp_uri(self):
        """Test TOTP URI generation for QR codes"""
        username = "test@example.com"
        secret = "JBSWY3DPEHPK3PXP"
        
        uri = MFAManager.generate_totp_uri(username, secret, issuer="RoXX")
        
        # Should be valid TOTP URI
        assert uri.startswith("otpauth://totp/")
        # Email gets URL-encoded (@ becomes %40)
        assert "test%40example.com" in uri or "test@example.com" in uri
        assert secret in uri
        assert "issuer=RoXX" in uri
    
    def test_generate_qr_code(self):
        """Test QR code image generation"""
        uri = "otpauth://totp/RoXX:test@example.com?secret=JBSWY3DPEHPK3PXP&issuer=RoXX"
        
        qr_data = MFAManager.generate_qr_code(uri)
        
        # Should be data URL with base64 encoded PNG
        assert qr_data.startswith("data:image/png;base64,")
        assert len(qr_data) > 100  # Reasonable size for QR code
    
    def test_verify_totp_valid(self):
        """Test TOTP verification with valid token"""
        secret = "JBSWY3DPEHPK3PXP"
        
        # Generate current token
        totp = pyotp.TOTP(secret)
        current_token = totp.now()
        
        # Should verify successfully
        assert MFAManager.verify_totp(secret, current_token) is True
    
    def test_verify_totp_invalid(self):
        """Test TOTP verification with invalid token"""
        secret = "JBSWY3DPEHPK3PXP"
        invalid_token = "000000"
        
        # Should reject invalid token
        assert MFAManager.verify_totp(secret, invalid_token) is False
    
    def test_verify_totp_window(self):
        """Test TOTP verification with time window"""
        secret = "JBSWY3DPEHPK3PXP"
        totp = pyotp.TOTP(secret)
        
        # Get token from previous time window (30 seconds ago)
        import time
        past_time = int(time.time()) - 30
        past_token = totp.at(past_time)
        
        # Should verify with window=1 (allows ±30 seconds)
        assert MFAManager.verify_totp(secret, past_token, valid_window=1) is True
        
        # Should reject with window=0 (current time only)
        assert MFAManager.verify_totp(secret, past_token, valid_window=0) is False
    
    def test_generate_backup_codes(self):
        """Test backup code generation"""
        plain_codes, hashed_codes = MFAManager.generate_backup_codes(count=10)
        
        # Should generate 10 codes
        assert len(plain_codes) == 10
        assert len(hashed_codes) == 10
        
        # Plain codes should be 8 hex characters
        for code in plain_codes:
            assert len(code) == 8
            assert all(c in '0123456789ABCDEF' for c in code)
        
        # Hashed codes should be SHA-256 hashes
        for hashed in hashed_codes:
            assert len(hashed) == 64  # SHA-256 hex digest
            assert all(c in '0123456789abcdef' for c in hashed)
        
        # All codes should be unique
        assert len(set(plain_codes)) == 10
        assert len(set(hashed_codes)) == 10
    
    def test_verify_backup_code_valid(self):
        """Test backup code verification with valid code"""
        plain_codes, hashed_codes = MFAManager.generate_backup_codes(count=5)
        
        # Verify first code
        is_valid, matched_hash = MFAManager.verify_backup_code(plain_codes[0], hashed_codes)
        
        assert is_valid is True
        assert matched_hash == hashed_codes[0]
    
    def test_verify_backup_code_invalid(self):
        """Test backup code verification with invalid code"""
        _, hashed_codes = MFAManager.generate_backup_codes(count=5)
        
        invalid_code = "INVALID1"
        is_valid, matched_hash = MFAManager.verify_backup_code(invalid_code, hashed_codes)
        
        assert is_valid is False
        assert matched_hash is None
    
    def test_verify_backup_code_case_insensitive(self):
        """Test backup code verification is case-insensitive"""
        plain_codes, hashed_codes = MFAManager.generate_backup_codes(count=1)
        
        # Test lowercase
        is_valid, _ = MFAManager.verify_backup_code(plain_codes[0].lower(), hashed_codes)
        assert is_valid is True
        
        # Test mixed case
        mixed_case = ''.join(
            c.lower() if i % 2 else c.upper() 
            for i, c in enumerate(plain_codes[0])
        )
        is_valid, _ = MFAManager.verify_backup_code(mixed_case, hashed_codes)
        assert is_valid is True
    
    def test_get_time_remaining(self):
        """Test getting time remaining for current TOTP"""
        remaining = MFAManager.get_time_remaining()
        
        # Should be between 0 and 30 seconds
        assert 0 <= remaining <= 30
        assert isinstance(remaining, int)
    
    def test_different_secrets_generate_different_tokens(self):
        """Test that different secrets generate different tokens"""
        secret1 = MFAManager.generate_secret()
        secret2 = MFAManager.generate_secret()
        
        totp1 = pyotp.TOTP(secret1)
        totp2 = pyotp.TOTP(secret2)
        
        token1 = totp1.now()
        token2 = totp2.now()
        
        # Different secrets should generate different tokens 
        # (extremely unlikely to be same)
        assert token1 != token2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
