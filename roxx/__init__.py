"""
RoXX - Linux RADIUS Authentication Proxy
"""

__version__ = "2.0.0"
__author__ = ""

from roxx.utils.system import SystemManager
from roxx.core.services import ServiceManager

__all__ = ["SystemManager", "ServiceManager", "__version__"]
