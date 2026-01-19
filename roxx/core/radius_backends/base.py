"""
Base Abstract Class for RADIUS Authentication Backends
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Optional
import logging

logger = logging.getLogger("roxx.radius_backends")


class RadiusBackend(ABC):
    """
    Abstract base class for all RADIUS authentication backends.
    
    All backend implementations must inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, config: dict):
        """
        Initialize backend with configuration.
        
        Args:
            config: Backend-specific configuration dictionary
        """
        self.config = config
        self.name = config.get('name', 'Unnamed Backend')
        self.enabled = config.get('enabled', True)
    
    @abstractmethod
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate user credentials.
        
        Args:
            username: Username to authenticate
            password: Password to verify
            
        Returns:
            Tuple of (success: bool, radius_attributes: dict or None)
            If successful, radius_attributes should contain RADIUS reply attributes
            like Reply-Message, Framed-IP-Address, etc.
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test backend connectivity and configuration.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass
    
    def get_user_attributes(self, username: str) -> Dict:
        """
        Get user attributes for RADIUS response.
        Default implementation returns empty dict.
        
        Args:
            username: Username to get attributes for
            
        Returns:
            Dictionary of RADIUS attributes
        """
        return {}
    
    def is_enabled(self) -> bool:
        """Check if backend is enabled"""
        return self.enabled
    
    def get_name(self) -> str:
        """Get backend name"""
        return self.name
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"
