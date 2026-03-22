"""
Linux System Utilities
Provides Linux-specific abstractions for system operations
"""

import os
import platform
import subprocess
import psutil
import datetime
from pathlib import Path
from typing import Optional

class SystemManager:
    """Linux System Utilities"""
    
    @staticmethod
    def get_os() -> str:
        """Returns the operating system description"""
        try:
            # Try to get pretty name from os-release
            if Path("/etc/os-release").exists():
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=")[1].strip().strip('"')
            
            # Fallback to platform
            return platform.system() + " " + platform.release()
        except:
            return "Linux (Unknown)"
            
    @staticmethod
    def get_kernel_version() -> str:
        """Returns the kernel version"""
        try:
            return platform.release()
        except:
            return "Unknown"

    @staticmethod
    def get_uptime() -> str:
        """Returns system uptime string"""
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot_time
            # Format: "2 days, 4:32"
            return str(uptime).split('.')[0]
        except:
            return "Unknown"

    @staticmethod
    def get_cpu_info() -> dict:
        """Returns CPU usage and count"""
        try:
            return {
                "percent": psutil.cpu_percent(interval=None),
                "count": psutil.cpu_count()
            }
        except:
            return {"percent": 0, "count": 1}

    @staticmethod
    def get_memory_info() -> dict:
        """Returns RAM usage"""
        try:
            mem = psutil.virtual_memory()
            return {
                "total": round(mem.total / (1024**3), 1), # GB
                "used": round(mem.used / (1024**3), 1),   # GB
                "percent": mem.percent
            }
        except:
            return {"total": 0, "used": 0, "percent": 0}

    @staticmethod
    def get_disk_info() -> dict:
        """Returns Disk usage for /"""
        try:
            disk = psutil.disk_usage('/')
            return {
                "total": round(disk.total / (1024**3), 1),
                "free": round(disk.free / (1024**3), 1),
                "percent": disk.percent
            }
        except:
            return {"total": 0, "free": 0, "percent": 0}

    @staticmethod
    def get_advanced_metrics() -> dict:
        """Returns IO counters and Load averages"""
        try:
            # IO Counters
            io = psutil.disk_io_counters()
            net = psutil.net_io_counters()
            
            # Load Avg (Unix only usually, but psutil handles basic)
            # On Windows getloadavg might not work, fallback to cpu percent
            try:
                if hasattr(os, 'getloadavg'):
                    load = os.getloadavg()
                else:
                    load = (psutil.cpu_percent(), 0, 0)
            except:
                load = (0, 0, 0)

            return {
                "disk_read_mb": round(io.read_bytes / (1024**2), 2),
                "disk_write_mb": round(io.write_bytes / (1024**2), 2),
                "net_sent_mb": round(net.bytes_sent / (1024**2), 2),
                "net_recv_mb": round(net.bytes_recv / (1024**2), 2),
                "load_1m": load[0],
                "load_5m": load[1],
                "process_count": len(psutil.pids()),
                # "Disk Busy" is hard to calculate instantly without interval, 
                # but we can use a placeholder or recent CPU wait if available.
                # For now, we'll return raw counters and let frontend diff them or show stat.
            }
        except Exception as e:
            print(f"Metrics Error: {e}")
            return {
                "disk_read_mb": 0, "disk_write_mb": 0,
                "net_sent_mb": 0, "net_recv_mb": 0,
                "load_1m": 0, "load_5m": 0,
                "process_count": 0
            }

    @staticmethod
    def is_service_running(service_name: str) -> bool:
        """Checks if a process is running"""
        try:
            for proc in psutil.process_iter(['name']):
                if service_name in proc.info['name']:
                    return True
            return False
        except:
            return False

    @staticmethod
    def is_admin() -> bool:
        """Checks if the program is running with root privileges"""
        try:
            return os.geteuid() == 0
        except:
            return False
    
    @staticmethod
    def get_config_dir() -> Path:
        """
        Returns config directory.
        Priority:
        1. ROXX_CONFIG_DIR environment variable
        2. Local 'config' directory (Dev convenience)
        3. /etc/roxx (Default)
        """
        if 'ROXX_CONFIG_DIR' in os.environ:
            return Path(os.environ['ROXX_CONFIG_DIR'])
            
        # Dev Convenience: Check local config dir first
        local_config = Path("config")
        if local_config.exists() and local_config.is_dir():
             return local_config.absolute()
             
        return Path('/etc/roxx')
    
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
            # Ensure config directory exists (crucial for local dev/Windows)
            if not users_file.parent.exists():
                users_file.parent.mkdir(parents=True, exist_ok=True)

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

