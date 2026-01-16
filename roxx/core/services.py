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
    """Linux Service Management (systemd)"""

    # Service names
    SERVICES = {
        'freeradius': 'freeradius',
        'winbind': 'winbind',
        'smbd': 'smbd',
        'nmbd': 'nmbd',
    }

    def __init__(self):
        pass

    def get_status(self, service: str) -> ServiceStatus:
        """
        Gets the status of a service via systemctl
        """
        service_name = self.SERVICES.get(service, service)
        
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return ServiceStatus.RUNNING if result.returncode == 0 else ServiceStatus.STOPPED
        except Exception:
            # Fallback: check via psutil
            return self._get_status_by_process(service_name)

    def _get_status_by_process(self, service_name: str) -> ServiceStatus:
        """Fallback: check via running processes"""
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if service_name.lower() in proc.info['name'].lower():
                        return ServiceStatus.RUNNING
                    if proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline']).lower()
                        if service_name.lower() in cmdline:
                            return ServiceStatus.RUNNING
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return ServiceStatus.STOPPED
        except:
            return ServiceStatus.UNKNOWN

    def start(self, service: str) -> bool:
        """Start a service"""
        service_name = self.SERVICES.get(service, service)
        try:
            subprocess.run(['systemctl', 'start', service_name], check=True, timeout=10)
            return True
        except subprocess.CalledProcessError:
            return False

    def stop(self, service: str) -> bool:
        """Stop a service"""
        service_name = self.SERVICES.get(service, service)
        try:
            subprocess.run(['systemctl', 'stop', service_name], check=True, timeout=10)
            return True
        except subprocess.CalledProcessError:
            return False

    def restart(self, service: str) -> bool:
        """Restart a service"""
        service_name = self.SERVICES.get(service, service)
        try:
            subprocess.run(['systemctl', 'restart', service_name], check=True, timeout=10)
            return True
        except subprocess.CalledProcessError:
            return False

    def get_all_services_status(self) -> dict:
        """Returns the status of all configured services"""
        return {
            service: self.get_status(service)
            for service in self.SERVICES.keys()
        }

