"""
Unit tests for ServiceManager
"""

import pytest
from unittest.mock import Mock, patch

from roxx.core.services import ServiceManager, ServiceStatus


class TestServiceManager:
    """Test ServiceManager functionality"""
    
    def test_init(self):
        """Test ServiceManager initialization"""
        mgr = ServiceManager()
        assert mgr.os_type == 'linux'
    
    def test_get_service_name(self):
        """Test service name mapping"""
        mgr = ServiceManager()
        
        # Test known service
        service_name = mgr._get_service_name('freeradius')
        assert service_name is not None
        
        # Test unknown service
        unknown = mgr._get_service_name('unknown_service_xyz')
        assert unknown == 'unknown_service_xyz'
    
    @patch('subprocess.run')
    def test_get_status_linux(self, mock_run):
        """Test service status on Linux"""
        mgr = ServiceManager()
        mgr.os_type = 'linux'
        
        # Mock successful status check
        mock_run.return_value = Mock(returncode=0)
        status = mgr._get_status_linux('freeradius')
        assert status == ServiceStatus.RUNNING
        
        # Mock stopped service
        mock_run.return_value = Mock(returncode=3)
        status = mgr._get_status_linux('freeradius')
        assert status == ServiceStatus.STOPPED
    
    @patch('subprocess.run')
    def test_start_service(self, mock_run):
        """Test starting a service"""
        mgr = ServiceManager()
        mgr.os_type = 'linux'
        
        mock_run.return_value = Mock(returncode=0)
        result = mgr.start('freeradius')
        assert result is True
        
        mock_run.side_effect = Exception("Failed")
        result = mgr.start('freeradius')
        assert result is False
    
    @patch('subprocess.run')
    def test_stop_service(self, mock_run):
        """Test stopping a service"""
        mgr = ServiceManager()
        mgr.os_type = 'linux'
        
        mock_run.return_value = Mock(returncode=0)
        result = mgr.stop('freeradius')
        assert result is True
    
    @patch('subprocess.run')
    def test_restart_service(self, mock_run):
        """Test restarting a service"""
        mgr = ServiceManager()
        mgr.os_type = 'linux'
        
        mock_run.return_value = Mock(returncode=0)
        result = mgr.restart('freeradius')
        assert result is True
    
    def test_get_all_services_status(self):
        """Test getting all services status"""
        mgr = ServiceManager()
        statuses = mgr.get_all_services_status()
        
        assert isinstance(statuses, dict)
        assert 'freeradius' in statuses
        assert all(isinstance(s, ServiceStatus) for s in statuses.values())
