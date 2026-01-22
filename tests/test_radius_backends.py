"""
Unit tests for RADIUS backends functionality
"""

import pytest
from roxx.core.radius_backends.cache import AuthCache
from roxx.core.radius_backends.config_db import RadiusBackendDB


class TestAuthCache:
    """Test authentication cache"""
    
    def test_cache_set_and_get(self):
        """Test setting and getting from cache"""
        cache = AuthCache(ttl=60)
        
        # Set value
        attrs = {'Framed-IP-Address': '10.0.0.1', 'Class': 'staff'}
        cache.set('testuser', 'password123', attrs)
        
        # Get value
        result = cache.get('testuser', 'password123')
        
        assert result is not None
        assert result[0] is True  # success
        assert result[1] == attrs
    
    def test_cache_miss(self):
        """Test cache miss"""
        cache = AuthCache(ttl=60)
        
        result = cache.get('nonexistent', 'password')
        
        assert result is None
    
    def test_cache_wrong_password(self):
        """Test cache with wrong password"""
        cache = AuthCache(ttl=60)
        
        cache.set('testuser', 'correct', {'attr': 'value'})
        
        result = cache.get('testuser', 'wrong')
        
        assert result is None
    
    def test_cache_stats(self):
        """Test cache hit/miss statistics"""
        cache = AuthCache(ttl=60)
        
        cache.set('user1', 'pass1', {})
        cache.set('user2', 'pass2', {})
        
        # Hits
        cache.get('user1', 'pass1')
        cache.get('user2', 'pass2')
        
        # Misses
        cache.get('user3', 'pass3')
        cache.get('user1', 'wrongpass')
        
        stats = cache.get_stats()
        
        # user1 is removed due to wrong password attempt
        assert stats['size'] == 1
        assert stats['hits'] == 2
        assert stats['misses'] == 2
        assert stats['hit_rate'] == 50.0
    
    def test_cache_clear(self):
        """Test clearing cache"""
        cache = AuthCache(ttl=60)
        
        cache.set('user1', 'pass1', {})
        cache.set('user2', 'pass2', {})
        
        assert cache.get_stats()['size'] == 2
        
        cache.clear()
        
        assert cache.get_stats()['size'] == 0
        assert cache.get('user1', 'pass1') is None


class TestRadiusBackendDB:
    """Test RADIUS backend database operations"""
    
    @classmethod
    def setup_class(cls):
        """Initialize database before tests"""
        # Use temp DB
        from pathlib import Path
        import tempfile
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_backends.db"
        
        RadiusBackendDB.set_db_path(cls.db_path)
        RadiusBackendDB.init()

    @classmethod
    def teardown_class(cls):
        """Clean up temp dir"""
        cls.temp_dir.cleanup()
    
    def test_create_backend(self):
        """Test creating a RADIUS backend"""
        success, message, backend_id = RadiusBackendDB.create_backend(
            backend_type='file',
            name='Test File Backend',
            config={'file_path': '/tmp/test.conf', 'password_type': 'bcrypt'},
            priority=100,
            enabled=True
        )
        
        assert success is True
        assert backend_id is not None
        assert backend_id > 0
    
    def test_list_backends(self):
        """Test listing all backends"""
        # Create a backend
        RadiusBackendDB.create_backend(
            backend_type='file',
            name='List Test Backend',
            config={'file_path': '/tmp/list.conf'},
            priority=200
        )
        
        backends = RadiusBackendDB.list_backends()
        
        assert isinstance(backends, list)
        assert len(backends) > 0
        
        # Check structure
        backend = backends[0]
        assert 'id' in backend
        assert 'backend_type' in backend
        assert 'name' in backend
        assert 'config' in backend
        assert 'priority' in backend
        assert 'enabled' in backend
    
    def test_update_backend(self):
        """Test updating backend"""
        # Create backend
        _, _, backend_id = RadiusBackendDB.create_backend(
            backend_type='file',
            name='Update Test',
            config={'file_path': '/tmp/old.conf'},
            priority=100
        )
        
        # Update it
        success, message = RadiusBackendDB.update_backend(
            backend_id=backend_id,
            name='Updated Name',
            config={'file_path': '/tmp/new.conf'},
            priority=50,
            enabled=False
        )
        
        assert success is True
        
        # Verify update
        backends = RadiusBackendDB.list_backends()
        updated = next((b for b in backends if b['id'] == backend_id), None)
        
        assert updated is not None
        assert updated['name'] == 'Updated Name'
        assert updated['priority'] == 50
        assert bool(updated['enabled']) is False
    
    def test_delete_backend(self):
        """Test deleting backend"""
        # Create backend
        _, _, backend_id = RadiusBackendDB.create_backend(
            backend_type='file',
            name='Delete Test',
            config={},
            priority=100
        )
        
        # Delete it
        success, message = RadiusBackendDB.delete_backend(backend_id)
        
        assert success is True
        
        # Verify deletion
        backends = RadiusBackendDB.list_backends()
        deleted = next((b for b in backends if b['id'] == backend_id), None)
        
        assert deleted is None
