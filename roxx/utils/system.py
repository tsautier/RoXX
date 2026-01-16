"""
Multi-OS System Utilities
Provides cross-platform abstractions for system operations
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional


class SystemManager:
    """Multi-OS abstraction for system operations"""
    
    @staticmethod
    def get_os() -> str:
        """
        Returns the operating system name
        Returns: 'windows', 'linux', or 'darwin' (macOS)
        """
        return platform.system().lower()
    
    @staticmethod
    def is_admin() -> bool:
        """Checks if the program is running with administrator privileges"""
        try:
            if SystemManager.get_os() == 'windows':
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                # Linux/macOS: check if root (UID 0)
                return os.geteuid() == 0
        except:
            return False
    
    @staticmethod
    def get_config_dir() -> Path:
        """Returns the configuration directory according to the OS"""
        os_type = SystemManager.get_os()
        
        if os_type == 'windows':
            return Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / 'RoXX'
        else:
            # Linux/macOS
            return Path('/usr/local/etc')
    
    @staticmethod
    def get_data_dir() -> Path:
        """Application data directory"""
        os_type = SystemManager.get_os()
        
        if os_type == 'windows':
            return Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / 'RoXX' / 'data'
        else:
            return Path('/usr/local/var')
    
    @staticmethod
    def get_log_dir() -> Path:
        """Log directory"""
        os_type = SystemManager.get_os()
        
        if os_type == 'windows':
            return Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / 'RoXX' / 'logs'
        else:
            return Path('/var/log/roxx')
    
    @staticmethod
    def run_command(
        command: list,
        check: bool = False,
        capture_output: bool = True,
        text: bool = True,
        timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess:
        """
        Executes a system command in a cross-platform way
        
        Args:
            command: Command and arguments as a list
            check: Raise exception if return code != 0
            capture_output: Capture stdout/stderr
            text: Return output as string (not bytes)
            timeout: Timeout in seconds
            
        Returns:
            CompletedProcess with stdout, stderr, returncode
        """
        return subprocess.run(
            command,
            check=check,
            capture_output=capture_output,
            text=text,
            timeout=timeout
        )
    
    @staticmethod
    def ensure_directories():
        """Creates necessary directories if they don't exist"""
        dirs = [
            SystemManager.get_config_dir(),
            SystemManager.get_data_dir(),
            SystemManager.get_log_dir(),
        ]
        
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def get_temp_dir() -> Path:
        """Multi-OS temporary directory"""
        import tempfile
        return Path(tempfile.gettempdir())
