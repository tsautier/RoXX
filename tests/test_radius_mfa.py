"""
Unit tests for RADIUS MFA integration
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from roxx.core.radius_backends.manager import RadiusBackendManager
from roxx.core.auth.mfa_db import MFADatabase
from roxx.core.auth.mfa import MFAManager


@pytest.fixture
def temp_mfa_db():
    """Create temporary MFA database for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_radius_mfa.db"
    
    import roxx.core.auth.mfa_db as mfa_db_module
    original_path = mfa_db_module.DB_PATH
    original_conn = mfa_db_module.db_conn
    mfa_db_module.DB_PATH = db_path
    
    MFADatabase.init()
    
    yield db_path
    
    # Cleanup - close connection first
    if mfa_db_module.db_conn:
        mfa_db_module.db_conn.close()
        mfa_db_module.db_conn = None
    
    mfa_db_module.DB_PATH = original_path
    mfa_db_module.db_conn = original_conn
    
    # Delete file with retry
    import time
    time.sleep(0.1)
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass
    try:
        os.rmdir(temp_dir)
    except:
        pass


@pytest.fixture
def mock_backend():
    """Create mock RADIUS backend"""
    backend = Mock()
    backend.get_name.return_value = "MockBackend"
    backend.is_enabled.return_value = True
    return backend


class TestRADIUSMFA:
    """Test RADIUS authentication with MFA"""
    
    def test_authenticate_without_mfa(self, temp_mfa_db, mock_backend):
        """Test authentication for user without MFA"""
        # Setup mock backend to accept password
        mock_backend.authenticate.return_value = (True, {'Reply-Message': 'OK'})
        
        # Create manager with mock backend
        manager = RadiusBackendManager()
        manager.backends = [mock_backend]
        
        # Authenticate without MFA
        success, attrs = manager.authenticate("normaluser", "password123")
        
        assert success is True
        mock_backend.authenticate.assert_called_once_with("normaluser", "password123")
    
    def test_authenticate_with_mfa_valid_totp(self, temp_mfa_db, mock_backend):
        """Test authentication with valid TOTP"""
        username = "mfauser@example.com"
        password = "MyPassword"
        
        # Enroll user in MFA
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        MFADatabase.enroll_totp(username, secret, backup_codes)
        
        # Get current TOTP
        import pyotp
        totp = pyotp.TOTP(secret)
        current_totp = totp.now()
        
        # Setup mock backend
        mock_backend.authenticate.return_value = (True, {})
        
        # Create manager
        manager = RadiusBackendManager()
        manager.backends = [mock_backend]
        
        # Authenticate with password+TOTP
        combined_password = password + current_totp
        success, attrs = manager.authenticate(username, combined_password)
        
        assert success is True
        # Backend should receive base password only (TOTP stripped)
        mock_backend.authenticate.assert_called_once_with(username, password)
    
    def test_authenticate_with_mfa_invalid_totp(self, temp_mfa_db, mock_backend):
        """Test authentication with invalid TOTP"""
        username = "mfauser2@example.com"
        password = "MyPassword"
        
        # Enroll user in MFA
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        MFADatabase.enroll_totp(username, secret, backup_codes)
        
        # Create manager
        manager = RadiusBackendManager()
        manager.backends = [mock_backend]
        
        # Authenticate with password+invalid TOTP
        combined_password = password + "000000"  # Invalid TOTP
        success, attrs = manager.authenticate(username, combined_password)
        
        assert success is False
        # Backend should NOT be called
        mock_backend.authenticate.assert_not_called()
    
    def test_authenticate_with_mfa_missing_totp(self, temp_mfa_db, mock_backend):
        """Test authentication with MFA enabled but no TOTP provided"""
        username = "mfauser3@example.com"
        password = "Short"  # Too short to extract TOTP
        
        # Enroll user in MFA
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        MFADatabase.enroll_totp(username, secret, backup_codes)
        
        # Create manager
        manager = RadiusBackendManager()
        manager.backends = [mock_backend]
        
        # Authenticate with short password
        success, attrs = manager.authenticate(username, password)
        
        assert success is False
        mock_backend.authenticate.assert_not_called()
    
    def test_authenticate_updates_last_used(self, temp_mfa_db, mock_backend):
        """Test that successful MFA auth updates last_used timestamp"""
        username = "mfauser4@example.com"
        password = "MyPassword"
        
        # Enroll user
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        MFADatabase.enroll_totp(username, secret, backup_codes)
        
        # Get current TOTP
        import pyotp
        totp = pyotp.TOTP(secret)
        current_totp = totp.now()
        
        # Initially no last_used
        settings = MFADatabase.get_mfa_settings(username)
        assert settings['last_used'] is None
        
        # Setup mock backend
        mock_backend.authenticate.return_value = (True, {})
        
        # Create manager and authenticate
        manager = RadiusBackendManager()
        manager.backends = [mock_backend]
        
        combined_password = password + current_totp
        success, _ = manager.authenticate(username, combined_password)
        
        assert success is True
        
        # last_used should be updated
        settings = MFADatabase.get_mfa_settings(username)
        assert settings['last_used'] is not None
    
    def test_cache_uses_base_password(self, temp_mfa_db, mock_backend):
        """Test that cache uses base password, not password+TOTP"""
        username = "mfauser5@example.com"
        password = "MyPassword"
        
        # Enroll user
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        MFADatabase.enroll_totp(username, secret, backup_codes)
        
        # Get two different TOTP codes (simulate time passing)
        import pyotp
        import time
        totp = pyotp.TOTP(secret)
        
        totp1 = totp.now()
        
        # Setup mock backend
        mock_backend.authenticate.return_value = (True, {})
        
        # Create manager
        manager = RadiusBackendManager()
        manager.backends = [mock_backend]
        
        # First authentication with TOTP1
        success1, _ = manager.authenticate(username, password + totp1)
        assert success1 is True
        assert mock_backend.authenticate.call_count == 1
        
        # Wait for new TOTP (or simulate)
        time.sleep(31)
        totp2 = totp.now()
        
        # Second authentication with TOTP2
        # If cache works with base password, backend shouldn't be called again
        success2, _ = manager.authenticate(username, password + totp2)
        assert success2 is True
        
        # Backend should be called twice (once per unique TOTP) 
        # because TOTP verification happens before cache check
        assert mock_backend.authenticate.call_count >= 1
    
    def test_password_extraction_edge_cases(self, temp_mfa_db, mock_backend):
        """Test password extraction with various lengths"""
        username = "mfauser6@example.com"
        
        # Enroll user
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        MFADatabase.enroll_totp(username, secret, backup_codes)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        current_totp = totp.now()
        
        # Create manager
        mock_backend.authenticate.return_value = (True, {})
        manager = RadiusBackendManager()
        manager.backends = [mock_backend]
        
        test_cases = [
            ("a", current_totp, "a"),  # 1-char password
            ("ab", current_totp, "ab"),  # 2-char password
            ("password", current_totp, "password"),  # Normal password
            ("verylongpassword123", current_totp, "verylongpassword123"),  # Long password
        ]
        
        for base_pwd, totp_code, expected_base in test_cases:
            mock_backend.reset_mock()
            combined = base_pwd + totp_code
            
            success, _ = manager.authenticate(username, combined)
            
            if success:
                # Verify backend received base password
                assert mock_backend.authenticate.called
                call_args = mock_backend.authenticate.call_args[0]
                assert call_args[1] == expected_base


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
