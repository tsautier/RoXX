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
        """/etc/roxx or ROXX_CONFIG_DIR"""
        return Path(os.getenv('ROXX_CONFIG_DIR', '/etc/roxx'))
    
    @staticmethod
    def get_data_dir() -> Path:
        """/var/lib/roxx or ROXX_DATA_DIR"""
        return Path(os.getenv('ROXX_DATA_DIR', '/var/lib/roxx'))
    
    @staticmethod
    def get_log_dir() -> Path:
        """/var/log/roxx or ROXX_LOG_DIR"""
        return Path(os.getenv('ROXX_LOG_DIR', '/var/log/roxx'))

    @staticmethod
    def get_radius_log_file() -> Path:
        """/var/log/freeradius/radius.log or ROXX_RADIUS_LOG"""
        return Path(os.getenv('ROXX_RADIUS_LOG', '/var/log/freeradius/radius.log'))

    @staticmethod
    def add_radius_user(username: str, password: str, attribute: str = "Cleartext-Password", op: str = ":=") -> bool:
        """Adds a user to users.conf"""
        try:
            users_file = SystemManager.get_config_dir() / "users.conf"
            # format: username attribute op password
            entry = f'{username} {attribute} {op} "{password}"\n'
            
            # Simple append (not checking duplicates for MVP flexibility, but ideally should)
            # Better: read, filter, append.
            current_lines = []
            if users_file.exists():
                with open(users_file, 'r') as f:
                    current_lines = f.readlines()
            
            # Remove existing user if any to avoid duplicates
            clean_lines = [l for l in current_lines if not l.strip().startswith(f"{username} ")]
            clean_lines.append(entry)
            
            with open(users_file, 'w') as f:
                f.writelines(clean_lines)
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False

    @staticmethod
    def delete_radius_user(username: str) -> bool:
        """Removes a user from users.conf"""
        try:
            users_file = SystemManager.get_config_dir() / "users.conf"
            if not users_file.exists():
                return False
                
            with open(users_file, 'r') as f:
                lines = f.readlines()
            
            clean_lines = [l for l in lines if not l.strip().startswith(f"{username} ")]
            
            with open(users_file, 'w') as f:
                f.writelines(clean_lines)
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
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

