"""
Multi-OS service management for RoXX
"""

import subprocess
from enum import Enum
from typing import Optional
import psutil

from roxx.utils.system import SystemManager


class ServiceStatus(Enum):
    """Possible service states"""
    RUNNING = "UP"
    STOPPED = "DOWN"
    UNKNOWN = "UNKNOWN"


class ServiceManager:
    """Multi-OS system service management"""

    # Service name mapping by OS
    SERVICES = {
        'freeradius': {
            'linux': 'freeradius',
            'windows': 'FreeRADIUS',
            'darwin': 'org.freeradius.radiusd'
        },
        'winbind': {
            'linux': 'winbind',
            'windows': None,  # Doesn't exist on Windows
            'darwin': None
        },
        'smbd': {
            'linux': 'smbd',
            'windows': None,
            'darwin': 'com.samba.smbd'
        },
        'nmbd': {
            'linux': 'nmbd',
            'windows': None,
            'darwin': 'com.samba.nmbd'
        },
    }

    def __init__(self):
        self.os_type = SystemManager.get_os()

    def _get_service_name(self, service: str) -> Optional[str]:
        """Gets the service name for the current OS"""
        if service in self.SERVICES:
            return self.SERVICES[service].get(self.os_type)
        return service

    def get_status(self, service: str) -> ServiceStatus:
        """
        Gets the status of a service
        
        Args:
            service: Generic service name (e.g. 'freeradius')
        
        Returns:
            ServiceStatus enum
        """
        service_name = self._get_service_name(service)
        
        if not service_name:
            return ServiceStatus.UNKNOWN

        if self.os_type == 'linux':
            return self._get_status_linux(service_name)
        elif self.os_type == 'windows':
            return self._get_status_windows(service_name)
        elif self.os_type == 'darwin':
            return self._get_status_macos(service_name)
        else:
            return ServiceStatus.UNKNOWN

    def _get_status_linux(self, service: str) -> ServiceStatus:
        """Status via systemctl (Linux)"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True,
                timeout=5
            )
            return ServiceStatus.RUNNING if result.returncode == 0 else ServiceStatus.STOPPED
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback: check via psutil
            return self._get_status_by_process(service)

    def _get_status_windows(self, service: str) -> ServiceStatus:
        """Status via sc query (Windows)"""
        try:
            result = subprocess.run(
                ['sc', 'query', service],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'RUNNING' in result.stdout:
                return ServiceStatus.RUNNING
            elif 'STOPPED' in result.stdout:
                return ServiceStatus.STOPPED
            else:
                return ServiceStatus.UNKNOWN
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._get_status_by_process(service)

    def _get_status_macos(self, service: str) -> ServiceStatus:
        """Status via launchctl (macOS)"""
        try:
            result = subprocess.run(
                ['launchctl', 'list', service],
                capture_output=True,
                text=True,
                timeout=5
            )
            return ServiceStatus.RUNNING if result.returncode == 0 else ServiceStatus.STOPPED
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._get_status_by_process(service)

    def _get_status_by_process(self, service: str) -> ServiceStatus:
        """Fallback: check via running processes"""
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    # Check process name
                    if service.lower() in proc.info['name'].lower():
                        return ServiceStatus.RUNNING
                    # Check command line
                    if proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline']).lower()
                        if service.lower() in cmdline:
                            return ServiceStatus.RUNNING
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return ServiceStatus.STOPPED
        except:
            return ServiceStatus.UNKNOWN

    def start(self, service: str) -> bool:
        """Start a service"""
        service_name = self._get_service_name(service)
        if not service_name:
            return False

        try:
            if self.os_type == 'linux':
                subprocess.run(['systemctl', 'start', service_name], check=True, timeout=10)
            elif self.os_type == 'windows':
                subprocess.run(['sc', 'start', service_name], check=True, timeout=10)
            elif self.os_type == 'darwin':
                subprocess.run(['launchctl', 'start', service_name], check=True, timeout=10)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def stop(self, service: str) -> bool:
        """Stop a service"""
        service_name = self._get_service_name(service)
        if not service_name:
            return False

        try:
            if self.os_type == 'linux':
                subprocess.run(['systemctl', 'stop', service_name], check=True, timeout=10)
            elif self.os_type == 'windows':
                subprocess.run(['sc', 'stop', service_name], check=True, timeout=10)
            elif self.os_type == 'darwin':
                subprocess.run(['launchctl', 'stop', service_name], check=True, timeout=10)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def restart(self, service: str) -> bool:
        """Restart a service"""
        service_name = self._get_service_name(service)
        if not service_name:
            return False

        try:
            if self.os_type == 'linux':
                subprocess.run(['systemctl', 'restart', service_name], check=True, timeout=10)
            elif self.os_type == 'windows':
                # Windows doesn't have a direct restart command
                self.stop(service)
                import time
                time.sleep(2)
                self.start(service)
            elif self.os_type == 'darwin':
                subprocess.run(['launchctl', 'restart', service_name], check=True, timeout=10)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def get_all_services_status(self) -> dict:
        """Returns the status of all configured services"""
        return {
            service: self.get_status(service)
            for service in self.SERVICES.keys()
        }
