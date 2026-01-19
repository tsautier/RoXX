"""
File-based RADIUS Authentication Backend

Supports users.conf format for backward compatibility.
"""

from typing import Tuple, Dict, Optional
import logging
from pathlib import Path
import bcrypt

from .base import RadiusBackend

logger = logging.getLogger("roxx.radius_backends.file")


class FileRadiusBackend(RadiusBackend):
    """
    File-based authentication backend using users.conf format.
    
    Configuration options:
    - file_path: Path to users file (default: /etc/roxx/users.conf)
    - password_type: 'bcrypt', 'plain' (default: bcrypt)
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        self.file_path = Path(config.get('file_path', '/etc/roxx/users.conf'))
        self.password_type = config.get('password_type', 'bcrypt')
        self._users_cache = {}
        self._last_reload = 0
    
    def _load_users(self) -> Dict:
        """Load users from file into cache"""
        if not self.file_path.exists():
            logger.warning(f"Users file not found: {self.file_path}")
            return {}
        
        users = {}
        try:
            with open(self.file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Format: username  password  [attributes]
                    parts = line.split(None, 2)
                    if len(parts) >= 2:
                        username = parts[0]
                        password = parts[1]
                        attributes = {}
                        
                        if len(parts) == 3:
                            # Parse attributes (key=value pairs)
                            attr_str = parts[2]
                            for attr_pair in attr_str.split(','):
                                if '=' in attr_pair:
                                    key, value = attr_pair.split('=', 1)
                                    attributes[key.strip()] = value.strip()
                        
                        users[username] = {
                            'password': password,
                            'attributes': attributes
                        }
            
            logger.info(f"Loaded {len(users)} users from {self.file_path}")
            self._users_cache = users
            return users
            
        except Exception as e:
            logger.error(f"Error loading users file: {e}")
            return {}
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """Authenticate user from file"""
        if not username or not password:
            return False, None
        
        # Reload users (with caching logic)
        users = self._load_users()
        
        if username not in users:
            logger.warning(f"{self.name}: User {username} not found in file")
            return False, None
        
        user_data = users[username]
        stored_password = user_data['password']
        
        # Verify password
        try:
            if self.password_type == 'bcrypt':
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    logger.info(f"{self.name}: Authentication successful for {username}")
                    return True, user_data['attributes']
            elif self.password_type == 'plain':
                if password == stored_password:
                    logger.info(f"{self.name}: Authentication successful for {username}")
                    return True, user_data['attributes']
            
            logger.warning(f"{self.name}: Password verification failed for {username}")
            return False, None
            
        except Exception as e:
            logger.error(f"{self.name}: Error verifying password: {e}")
            return False, None
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test if file exists and is readable"""
        if not self.file_path.exists():
            return False, f"Users file not found: {self.file_path}"
        
        if not self.file_path.is_file():
            return False, f"Path is not a file: {self.file_path}"
        
        try:
            with open(self.file_path, 'r') as f:
                line_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
            return True, f"Successfully read users file ({line_count} users)"
        except Exception as e:
            return False, f"Cannot read file: {str(e)}"
    
    def get_user_attributes(self, username: str) -> Dict:
        """Get user attributes from file"""
        users = self._load_users()
        if username in users:
            return users[username]['attributes']
        return {}
