"""
inWebo/TrustBuilder Push Authentication Module
Linux replacement for bin/push.sh
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from enum import Enum

import httpx


class PushResult(Enum):
    """Possible results of a Push authentication"""
    SUCCESS = "OK"
    REFUSED = "REFUSED"
    TIMEOUT = "TIMEOUT"
    NO_PUSH = "NOPUSH"
    NO_APP = "NOMA"
    NO_LOGIN = "NOLOGIN"
    SYNTAX_ERROR = "SN"
    INVALID_SERVICE = "srv unknown"
    ERROR = "ERROR"


class InWeboAuthenticator:
    """
    inWebo/TrustBuilder client for Push authentication
    
    Modern Python replacement for the Bash push.sh script.
    """

    API_BASE_URL = "https://api.myinwebo.com/FS"
    
    def __init__(
        self,
        service_id: str,
        cert_path: Path,
        key_path: Path,
        proxy: Optional[str] = None,
        context: str = "Proxy_RoXX",
        max_attempts: int = 7,
        poll_interval: int = 3
    ):
        """
        Initialize the inWebo client
        
        Args:
            service_id: inWebo service ID
            cert_path: Path to client certificate (.pem)
            key_path: Path to private key (.pem)
            proxy: Proxy URL (optional)
            context: Authentication context
            max_attempts: Maximum number of polling attempts
            poll_interval: Interval between attempts (seconds)
        """
        self.service_id = service_id
        self.cert = (str(cert_path), str(key_path))
        self.proxy = proxy
        self.context = context
        self.max_attempts = max_attempts
        self.poll_interval = poll_interval
        
        self.logger = logging.getLogger(__name__)
        
        # Check that certificates exist
        if not cert_path.exists():
            raise FileNotFoundError(f"Certificate not found: {cert_path}")
        if not key_path.exists():
            raise FileNotFoundError(f"Private key not found: {key_path}")

    def _make_request(self, params: Dict[str, str]) -> Dict:
        """
        Make a request to the inWebo API
        
        Args:
            params: Request parameters
            
        Returns:
            JSON response from the API
            
        Raises:
            httpx.HTTPError: In case of network error
        """
        proxies = {'https': self.proxy} if self.proxy else None
        
        try:
            with httpx.Client(
                cert=self.cert,
                proxies=proxies,
                verify=True,
                timeout=10.0
            ) as client:
                response = client.get(self.API_BASE_URL, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error: {e}")
            raise

    def push_authenticate(self, username: str) -> Tuple[PushResult, Optional[str]]:
        """
        Trigger an inWebo Push authentication
        
        Args:
            username: Username (without quotes)
            
        Returns:
            Tuple (result, session_id or None)
        """
        # Clean username (remove quotes if present)
        username = username.strip('"')
        
        self.logger.info(f"Requesting Push authentication for {username}")
        
        params = {
            'action': 'pushAuthenticate',
            'serviceId': self.service_id,
            'userId': username,
            'format': 'json',
            'context': self.context
        }
        
        try:
            result = self._make_request(params)
        except httpx.HTTPError:
            return (PushResult.ERROR, None)
        
        # Parse the response
        error = result.get('err', '')
        
        if error == 'OK':
            session_id = result.get('sessionId')
            if session_id:
                return (PushResult.SUCCESS, session_id)
            else:
                self.logger.error("No sessionId in response")
                return (PushResult.ERROR, None)
        
        # Handle errors
        error_mapping = {
            'NOK:NOPUSH': PushResult.NO_PUSH,
            'NOK:NOMA': PushResult.NO_APP,
            'NOK:NOLOGIN': PushResult.NO_LOGIN,
            'NOK:SN': PushResult.SYNTAX_ERROR,
            'NOK:srv unknown': PushResult.INVALID_SERVICE,
        }
        
        push_result = error_mapping.get(error, PushResult.ERROR)
        self.logger.warning(f"Push request failed: {error}")
        
        return (push_result, None)

    def check_push_result(self, username: str, session_id: str) -> PushResult:
        """
        Check the result of a Push authentication (polling)
        
        Args:
            username: Username
            session_id: Session ID obtained during push
            
        Returns:
            Authentication result
        """
        username = username.strip('"')
        
        for attempt in range(1, self.max_attempts + 1):
            self.logger.debug(f"Checking push result, attempt {attempt}/{self.max_attempts}")
            
            params = {
                'action': 'checkPushResult',
                'serviceId': self.service_id,
                'userId': username,
                'sessionId': session_id,
                'format': 'json'
            }
            
            try:
                result = self._make_request(params)
            except httpx.HTTPError:
                return PushResult.ERROR
            
            error = result.get('err', '')
            
            # Success
            if error == 'OK':
                self.logger.info(f"Push authentication accepted by {username}")
                return PushResult.SUCCESS
            
            # Waiting
            if error == 'NOK:WAITING':
                if attempt < self.max_attempts:
                    time.sleep(self.poll_interval)
                    continue
                else:
                    # Timeout after all attempts
                    self.logger.warning(f"Push authentication timeout for {username}")
                    return PushResult.TIMEOUT
            
            # Other errors
            error_mapping = {
                'NOK:REFUSED': PushResult.REFUSED,
                'NOK:NOMA': PushResult.NO_APP,
                'NOK:TIMEOUT': PushResult.TIMEOUT,
                'NOK:SN': PushResult.SYNTAX_ERROR,
                'NOK:srv unknown': PushResult.INVALID_SERVICE,
            }
            
            push_result = error_mapping.get(error, PushResult.ERROR)
            self.logger.warning(f"Push authentication failed: {error}")
            return push_result
        
        # Should never reach here
        return PushResult.TIMEOUT

    def authenticate(self, username: str) -> PushResult:
        """
        Perform a complete Push authentication (push + polling)
        
        Args:
            username: Username
            
        Returns:
            Final authentication result
        """
        # Step 1: Trigger the Push
        result, session_id = self.push_authenticate(username)
        
        if result != PushResult.SUCCESS or not session_id:
            return result
        
        # Step 2: Check the result (polling)
        return self.check_push_result(username, session_id)


def main():
    """
    Entry point for command-line usage
    Compatible with FreeRADIUS exec module
    """
    import os
    import sys
    
    # Configuration (adapt according to environment)
    from roxx.utils.system import SystemManager
    
    config_dir = SystemManager.get_config_dir()
    cert_path = config_dir / "certs" / "iw_cert.pem"
    key_path = config_dir / "certs" / "iw_key.pem"
    
    # Get username from environment variables
    # (FreeRADIUS passes USER_NAME via environment)
    username = os.environ.get('USER_NAME', '')
    
    if not username:
        print("NOUSERNAME", end='')
        logging.warning("USER_NAME variable not found in environment")
        sys.exit(1)
    
    # Get configuration from file or environment variables
    service_id = os.environ.get('INWEBO_SERVICE_ID', '10408')
    proxy = os.environ.get('INWEBO_PROXY', None)
    
    try:
        authenticator = InWeboAuthenticator(
            service_id=service_id,
            cert_path=cert_path,
            key_path=key_path,
            proxy=proxy
        )
        
        result = authenticator.authenticate(username)
        
        if result == PushResult.SUCCESS:
            print("OK", end='')
            sys.exit(0)
        else:
            print(result.value, end='')
            sys.exit(1)
            
    except FileNotFoundError as e:
        print("ERRORCERT", end='')
        logging.error(f"Certificate error: {e}")
        sys.exit(1)
    except Exception as e:
        print("ERROR", end='')
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging for syslog
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s: %(message)s'
    )
    main()
