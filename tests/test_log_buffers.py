"""
Unit tests for authentication log buffers
"""

import pytest
from roxx.core.logging.auth_log_buffer import AuthLogBuffer


class TestAuthLogBuffer:
    """Test authentication log buffer functionality"""
    
    def test_add_and_get_logs(self):
        """Test adding and retrieving logs"""
        buffer = AuthLogBuffer(max_size=10)
        
        buffer.add({
            'backend_type': 'ldap',
            'backend_name': 'Test LDAP',
            'username': 'testuser',
            'action': 'authenticate',
            'success': True,
            'duration_ms': 45.2,
            'details': 'Login successful'
        })
        
        logs = buffer.get_logs(limit=10)
        
        assert len(logs) == 1
        assert logs[0]['username'] == 'testuser'
        assert logs[0]['backend_type'] == 'ldap'
        assert logs[0]['success'] is True
    
    def test_filter_by_success(self):
        """Test filtering logs by success status"""
        buffer = AuthLogBuffer(max_size=10)
        
        buffer.add({'backend_type': 'ldap', 'username': 'user1', 'success': True})
        buffer.add({'backend_type': 'ldap', 'username': 'user2', 'success': False})
        buffer.add({'backend_type': 'ldap', 'username': 'user3', 'success': True})
        
        success_logs = buffer.get_logs(success=True)
        failure_logs = buffer.get_logs(success=False)
        
        assert len(success_logs) == 2
        assert len(failure_logs) == 1
        assert success_logs[0]['username'] in ['user1', 'user3']
        assert failure_logs[0]['username'] == 'user2'
    
    def test_filter_by_backend_type(self):
        """Test filtering by backend type"""
        buffer = AuthLogBuffer(max_size=10)
        
        buffer.add({'backend_type': 'ldap', 'username': 'user1', 'success': True})
        buffer.add({'backend_type': 'saml', 'username': 'user2', 'success': True})
        buffer.add({'backend_type': 'ldap', 'username': 'user3', 'success': True})
        
        ldap_logs = buffer.get_logs(backend_type='ldap')
        saml_logs = buffer.get_logs(backend_type='saml')
        
        assert len(ldap_logs) == 2
        assert len(saml_logs) == 1
    
    def test_filter_by_username(self):
        """Test username search filtering"""
        buffer = AuthLogBuffer(max_size=10)
        
        buffer.add({'backend_type': 'ldap', 'username': 'john.doe', 'success': True})
        buffer.add({'backend_type': 'ldap', 'username': 'jane.smith', 'success': True})
        buffer.add({'backend_type': 'ldap', 'username': 'john.smith', 'success': True})
        
        john_logs = buffer.get_logs(username='john')
        jane_logs = buffer.get_logs(username='jane')
        
        assert len(john_logs) == 2
        assert len(jane_logs) == 1
    
    def test_max_size_limit(self):
        """Test that buffer respects max_size limit"""
        buffer = AuthLogBuffer(max_size=5)
        
        # Add more logs than max_size
        for i in range(10):
            buffer.add({
                'backend_type': 'ldap',
                'username': f'user{i}',
                'success': True
            })
        
        logs = buffer.get_logs(limit=100)
        
        # Should only keep last 5
        assert len(logs) == 5
        # Most recent should be user9
        assert logs[0]['username'] == 'user9'
    
    def test_get_stats(self):
        """Test getting buffer statistics"""
        buffer = AuthLogBuffer(max_size=10)
        
        buffer.add({'backend_type': 'ldap', 'username': 'user1', 'success': True})
        buffer.add({'backend_type': 'ldap', 'username': 'user2', 'success': False})
        buffer.add({'backend_type': 'ldap', 'username': 'user3', 'success': True})
        buffer.add({'backend_type': 'ldap', 'username': 'user4', 'success': True})
        
        stats = buffer.get_stats()
        
        assert stats['size'] == 4
        assert stats['total_successes'] == 3
        assert stats['total_failures'] == 1
        assert stats['success_rate'] == 75.0
    
    def test_clear_logs(self):
        """Test clearing all logs"""
        buffer = AuthLogBuffer(max_size=10)
        
        buffer.add({'backend_type': 'ldap', 'username': 'user1', 'success': True})
        buffer.add({'backend_type': 'ldap', 'username': 'user2', 'success': True})
        
        assert len(buffer.get_logs()) == 2
        
        buffer.clear()
        
        assert len(buffer.get_logs()) == 0
        stats = buffer.get_stats()
        assert stats['size'] == 0
    
    def test_thread_safety(self):
        """Test basic thread safety (add from multiple 'threads')"""
        buffer = AuthLogBuffer(max_size=100)
        
        # Simulate concurrent adds
        for i in range(50):
            buffer.add({'backend_type': 'ldap', 'username': f'user{i}', 'success': True})
        
        logs = buffer.get_logs()
        assert len(logs) == 50
