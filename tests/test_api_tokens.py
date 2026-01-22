"""
Unit tests for API Tokens functionality
"""

import pytest
from roxx.core.auth.api_tokens import APITokenManager


class TestAPITokens:
    """Test API token generation, verification, and revocation"""
    
    @classmethod
    def setup_class(cls):
        """Initialize token manager before tests"""
        # Use temp DB
        from pathlib import Path
        import tempfile
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_api_tokens.db"
        
        APITokenManager.set_db_path(cls.db_path)
        APITokenManager.init()

    @classmethod
    def teardown_class(cls):
        """Clean up temp dir"""
        cls.temp_dir.cleanup()
    
    def test_generate_token(self):
        """Test API token generation"""
        success, message, token = APITokenManager.generate_token("test-token")
        
        assert success is True
        assert token is not None
        assert len(token) == 43  # token_urlsafe(32) produces 43 chars
        assert "created" in message.lower() or "generated" in message.lower()
    
    def test_verify_valid_token(self):
        """Test verification of valid token"""
        # Generate token
        _, _, token = APITokenManager.generate_token("verify-test")
        
        # Verify it
        valid, name = APITokenManager.verify_token(token)
        
        assert valid is True
        assert name == "verify-test"
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        valid, name = APITokenManager.verify_token("invalid-token-12345")
        
        assert valid is False
        assert name is None
    
    def test_list_tokens(self):
        """Test listing API tokens"""
        # Generate a token
        APITokenManager.generate_token("list-test")
        
        # List tokens
        tokens = APITokenManager.list_tokens()
        
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        
        # Check token structure
        token = tokens[0]
        assert 'id' in token
        assert 'name' in token
        assert 'created_at' in token
        assert 'enabled' in token
        # Token itself should NOT be in list
        assert 'token' not in token
    
    def test_revoke_token(self):
        """Test token revocation"""
        # Generate token
        _, _, token = APITokenManager.generate_token("revoke-test")
        
        # Get token ID
        tokens = APITokenManager.list_tokens()
        token_id = None
        for t in tokens:
            if t['name'] == 'revoke-test':
                token_id = t['id']
                break
        
        assert token_id is not None
        
        # Revoke token
        success, message = APITokenManager.revoke_token(token_id)
        assert success is True
        
        # Verify token no longer works
        valid, _ = APITokenManager.verify_token(token)
        assert valid is False
    
    def test_token_last_used_tracking(self):
        """Test that token usage is tracked"""
        # Generate token
        _, _, token = APITokenManager.generate_token("usage-test")
        
        # Use it
        valid, _ = APITokenManager.verify_token(token)
        assert valid is True
        
        # Check last_used is set
        tokens = APITokenManager.list_tokens()
        test_token = next((t for t in tokens if t['name'] == 'usage-test'), None)
        
        assert test_token is not None
        assert test_token['last_used'] is not None
