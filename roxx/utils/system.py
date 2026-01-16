"""
Linux System Utilities
Provides Linux-specific abstractions for system operations
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional



class SystemManager:
    """Linux System Utilities"""
    
    @staticmethod
    def get_os() -> str:
        """Returns the operating system name"""
        return 'linux'
    
    @staticmethod
    def is_admin() -> bool:
        """Checks if the program is running with root privileges"""
        try:
            return os.geteuid() == 0
        except:
            return False
    
    @staticmethod
    def get_config_dir() -> Path:
        """/etc/roxx"""
        return Path('/etc/roxx')
    
    @staticmethod
    def get_data_dir() -> Path:
        """/var/lib/roxx"""
        return Path('/var/lib/roxx')
    
    @staticmethod
    def get_log_dir() -> Path:
        """/var/log/roxx"""
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
        Executes a system command
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
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                # Expected if not running as root during dev/test
                pass
    
    @staticmethod
    def get_temp_dir() -> Path:
        """Temporary directory"""
        import tempfile
        return Path(tempfile.gettempdir())

