"""
Unit tests for SystemManager
"""

import pytest
import platform
from pathlib import Path

from roxx.utils.system import SystemManager


class TestSystemManager:
    """Test SystemManager functionality"""
    
    def test_get_os(self):
        """Test OS detection"""
        os_type = SystemManager.get_os()
        assert os_type in ['linux', 'windows', 'darwin']
        assert os_type == platform.system().lower()
    
    def test_is_admin(self):
        """Test admin detection"""
        result = SystemManager.is_admin()
        assert isinstance(result, bool)
    
    def test_get_config_dir(self):
        """Test config directory path"""
        config_dir = SystemManager.get_config_dir()
        assert isinstance(config_dir, Path)
        
        # Verify path is OS-appropriate
        if SystemManager.get_os() == 'windows':
            assert 'ProgramData' in str(config_dir) or 'RoXX' in str(config_dir)
        else:
            assert str(config_dir).startswith('/usr/local')
    
    def test_get_data_dir(self):
        """Test data directory path"""
        data_dir = SystemManager.get_data_dir()
        assert isinstance(data_dir, Path)
    
    def test_get_log_dir(self):
        """Test log directory path"""
        log_dir = SystemManager.get_log_dir()
        assert isinstance(log_dir, Path)
    
    def test_get_temp_dir(self):
        """Test temp directory path"""
        temp_dir = SystemManager.get_temp_dir()
        assert isinstance(temp_dir, Path)
        assert 'roxx' in str(temp_dir).lower()
    
    def test_run_command_success(self):
        """Test successful command execution"""
        if SystemManager.get_os() == 'windows':
            result = SystemManager.run_command(['cmd', '/c', 'echo', 'test'])
        else:
            result = SystemManager.run_command(['echo', 'test'])
        
        assert result.returncode == 0
        assert 'test' in result.stdout
    
    def test_run_command_failure(self):
        """Test failed command execution"""
        with pytest.raises(Exception):
            SystemManager.run_command(['nonexistent_command_xyz'], check=True)
    
    def test_ensure_directories(self, tmp_path, monkeypatch):
        """Test directory creation"""
        # Mock the directory getters
        monkeypatch.setattr(SystemManager, 'get_config_dir', lambda: tmp_path / 'config')
        monkeypatch.setattr(SystemManager, 'get_data_dir', lambda: tmp_path / 'data')
        monkeypatch.setattr(SystemManager, 'get_log_dir', lambda: tmp_path / 'logs')
        
        SystemManager.ensure_directories()
        
        assert (tmp_path / 'config').exists()
        assert (tmp_path / 'data').exists()
        assert (tmp_path / 'logs').exists()
