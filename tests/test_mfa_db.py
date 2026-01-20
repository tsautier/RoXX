"""
Unit tests for MFA Database operations
"""

import pytest
import os
import tempfile
from pathlib import Path
from roxx.core.auth.mfa_db import MFADatabase
from roxx.core.auth.mfa import MFAManager


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_mfa.db"
    
    # Override DB path
    import roxx.core.auth.mfa_db as mfa_db_module
    original_path = mfa_db_module.DB_PATH
    mfa_db_module.DB_PATH = db_path
    
    # Initialize database
    MFADatabase.init()
    
    yield db_path
    
    # Cleanup
    mfa_db_module.DB_PATH = original_path
    if db_path.exists():
        db_path.unlink()
    os.rmdir(temp_dir)


class TestMFADatabase:
    """Test MFA Database operations"""
    
    def test_database_initialization(self, temp_db):
        """Test database file is created"""
        assert temp_db.exists()
    
    def test_enroll_totp(self, temp_db):
        """Test enrolling user in TOTP MFA"""
        username = "testuser@example.com"
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        
        success, message = MFADatabase.enroll_totp(username, secret, backup_codes)
        
        assert success is True
        assert "successfully" in message.lower()
    
    def test_get_mfa_settings(self, temp_db):
        """Test retrieving MFA settings"""
        username = "testuser2@example.com"
        secret = "TESTSECRET123456"
        _, backup_codes = MFAManager.generate_backup_codes(5)
        
        # Enroll user
        MFADatabase.enroll_totp(username, secret, backup_codes)
        
        # Retrieve settings
        settings = MFADatabase.get_mfa_settings(username)
        
        assert settings is not None
        assert settings['username'] == username
        assert settings['mfa_enabled'] == 1
        assert settings['mfa_type'] == 'totp'
        assert settings['totp_secret'] == secret
        assert len(settings['backup_codes']) == 5
    
    def test_get_mfa_settings_nonexistent_user(self, temp_db):
        """Test retrieving settings for non-existent user"""
        settings = MFADatabase.get_mfa_settings("nonexistent@example.com")
        assert settings is None
    
    def test_is_mfa_enabled(self, temp_db):
        """Test checking if MFA is enabled"""
        username = "testuser3@example.com"
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        
        # Before enrollment
        assert MFADatabase.is_mfa_enabled(username) is False
        
        # After enrollment
        MFADatabase.enroll_totp(username, secret, backup_codes)
        assert MFADatabase.is_mfa_enabled(username) is True
    
    def test_verify_and_consume_backup_code(self, temp_db):
        """Test verifying and consuming backup code"""
        username = "testuser4@example.com"
        secret = MFAManager.generate_secret()
        plain_codes, hashed_codes = MFAManager.generate_backup_codes(10)
        
        # Enroll user
        MFADatabase.enroll_totp(username, secret, hashed_codes)
        
        # Verify first backup code
        success, message = MFADatabase.verify_and_consume_backup_code(username, plain_codes[0])
        
        assert success is True
        assert "9 codes remaining" in message
        
        # Verify code was consumed
        settings = MFADatabase.get_mfa_settings(username)
        assert len(settings['backup_codes']) == 9
        
        # Try using same code again - should fail
        success, message = MFADatabase.verify_and_consume_backup_code(username, plain_codes[0])
        assert success is False
    
    def test_update_last_used(self, temp_db):
        """Test updating last used timestamp"""
        username = "testuser5@example.com"
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        
        # Enroll user
        MFADatabase.enroll_totp(username, secret, backup_codes)
        
        # Initially no last_used
        settings = MFADatabase.get_mfa_settings(username)
        assert settings['last_used'] is None
        
        # Update last used
        MFADatabase.update_last_used(username)
        
        # Should now have timestamp
        settings = MFADatabase.get_mfa_settings(username)
        assert settings['last_used'] is not None
    
    def test_disable_mfa(self, temp_db):
        """Test disabling MFA for user"""
        username = "testuser6@example.com"
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        
        # Enroll user
        MFADatabase.enroll_totp(username, secret, backup_codes)
        assert MFADatabase.is_mfa_enabled(username) is True
        
        # Disable MFA
        success, message = MFADatabase.disable_mfa(username)
        
        assert success is True
        assert "disabled" in message.lower()
        assert MFADatabase.is_mfa_enabled(username) is False
    
    def test_delete_mfa(self, temp_db):
        """Test deleting MFA settings"""
        username = "testuser7@example.com"
        secret = MFAManager.generate_secret()
        _, backup_codes = MFAManager.generate_backup_codes(10)
        
        # Enroll user
        MFADatabase.enroll_totp(username, secret, backup_codes)
        
        # Delete MFA
        success, message = MFADatabase.delete_mfa(username)
        
        assert success is True
        assert "deleted" in message.lower()
        
        # Settings should no longer exist
        settings = MFADatabase.get_mfa_settings(username)
        assert settings is None
    
    def test_list_mfa_users(self, temp_db):
        """Test listing all MFA users"""
        # Enroll multiple users
        for i in range(3):
            username = f"testuser{i}@example.com"
            secret = MFAManager.generate_secret()
            _, backup_codes = MFAManager.generate_backup_codes(10)
            MFADatabase.enroll_totp(username, secret, backup_codes)
        
        # List users
        users = MFADatabase.list_mfa_users()
        
        assert len(users) >= 3
        assert all('username' in user for user in users)
        assert all('mfa_enabled' in user for user in users)
    
    def test_reenroll_user(self, temp_db):
        """Test re-enrolling user (updates existing record)"""
        username = "testuser8@example.com"
        
        # First enrollment
        secret1 = "SECRET123456789ABCDEF"
        _, backup_codes1 = MFAManager.generate_backup_codes(10)
        MFADatabase.enroll_totp(username, secret1, backup_codes1)
        
        settings1 = MFADatabase.get_mfa_settings(username)
        created_at1 = settings1['created_at']
        
        # Re-enroll with new secret
        secret2 = "NEWSECRET123456789ABC"
        _, backup_codes2 = MFAManager.generate_backup_codes(10)
        MFADatabase.enroll_totp(username, secret2, backup_codes2)
        
        settings2 = MFADatabase.get_mfa_settings(username)
        
        # Secret should be updated
        assert settings2['totp_secret'] == secret2
        assert settings2['totp_secret'] != secret1
        
        # Backup codes should be new
        assert settings2['backup_codes'] != backup_codes1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
