"""
Unit tests for TOTP Authenticator
"""

import pytest
import time

from roxx.core.auth.totp import TOTPAuthenticator


class TestTOTPAuthenticator:
    """Test TOTP functionality"""
    
    def test_init(self):
        """Test TOTP initialization"""
        totp = TOTPAuthenticator(secret="JBSWY3DPEHPK3PXP")
        assert totp.secret == "JBSWY3DPEHPK3PXP"
        assert totp.digits == 6
        assert totp.period == 30
    
    def test_generate_code(self):
        """Test TOTP code generation"""
        totp = TOTPAuthenticator(secret="JBSWY3DPEHPK3PXP")
        code = totp.generate()
        
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()
    
    def test_verify_valid_code(self):
        """Test verifying a valid TOTP code"""
        totp = TOTPAuthenticator(secret="JBSWY3DPEHPK3PXP")
        
        # Generate a code and verify it immediately
        code = totp.generate()
        assert totp.verify(code) is True
    
    def test_verify_invalid_code(self):
        """Test verifying an invalid TOTP code"""
        totp = TOTPAuthenticator(secret="JBSWY3DPEHPK3PXP")
        
        # Use a clearly wrong code
        assert totp.verify("000000") is False
    
    def test_verify_with_window(self):
        """Test TOTP verification with time window"""
        totp = TOTPAuthenticator(secret="JBSWY3DPEHPK3PXP")
        
        # Generate code for past timestamp
        past_timestamp = int(time.time()) - 30
        past_code = totp.generate(past_timestamp)
        
        # Should still be valid with window=1
        assert totp.verify(past_code, window=1) is True
    
    def test_different_algorithms(self):
        """Test TOTP with different hash algorithms"""
        secret = "JBSWY3DPEHPK3PXP"
        
        totp_sha1 = TOTPAuthenticator(secret=secret, algorithm='SHA1')
        totp_sha256 = TOTPAuthenticator(secret=secret, algorithm='SHA256')
        totp_sha512 = TOTPAuthenticator(secret=secret, algorithm='SHA512')
        
        code_sha1 = totp_sha1.generate()
        code_sha256 = totp_sha256.generate()
        code_sha512 = totp_sha512.generate()
        
        # Different algorithms should produce different codes
        assert code_sha1 != code_sha256 or code_sha256 != code_sha512
    
    def test_invalid_secret(self):
        """Test TOTP with invalid secret"""
        totp = TOTPAuthenticator(secret="INVALID!!!")
        
        with pytest.raises(ValueError):
            totp.generate()
    
    def test_custom_digits(self):
        """Test TOTP with custom digit count"""
        totp = TOTPAuthenticator(secret="JBSWY3DPEHPK3PXP", digits=8)
        code = totp.generate()
        
        assert len(code) == 8
        assert code.isdigit()
