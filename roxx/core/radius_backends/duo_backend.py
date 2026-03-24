"""
Duo Security RADIUS authentication backend.
"""

from time import sleep
from typing import Dict, Optional, Tuple
import logging

from roxx.core.auth.duo import DuoProvider
from .base import RadiusBackend

logger = logging.getLogger("roxx.radius_backends.duo")


class DuoRadiusBackend(RadiusBackend):
    """
    Duo-backed authentication for RADIUS users.

    Configuration options:
    - integration_key: Duo integration key
    - secret_key: Duo secret key
    - api_hostname: Duo API hostname
    - factor: push, passcode, phone, sms
    - device: Duo device identifier (default: auto)
    - poll_interval: seconds between async status checks
    - poll_timeout: max seconds to wait for async approval
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.factor = config.get("factor", "push")
        self.device = config.get("device", "auto")
        self.poll_interval = int(config.get("poll_interval", 2))
        self.poll_timeout = int(config.get("poll_timeout", 30))
        self.provider = DuoProvider(config)

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        if not username:
            return False, None

        factor = self.factor
        passcode = password if factor == "passcode" else None

        preauth_ok, preauth = self.provider.preauth(username)
        if not preauth_ok:
            logger.warning("%s: Duo preauth failed for %s", self.name, username)
            return False, None

        preauth_result = preauth.get("result")
        if preauth_result == "deny":
            return False, None

        success, result = self.provider.auth(
            username,
            factor=factor,
            device=self.device,
            passcode=passcode,
        )
        if not success:
            return False, None

        if result.get("status") == "pending" and result.get("txid"):
            return self._poll_txid(result["txid"])

        if result.get("result") == "allow":
            return True, {"Reply-Message": "Authenticated via Duo"}

        return False, None

    def _poll_txid(self, txid: str) -> Tuple[bool, Optional[Dict]]:
        waited = 0
        while waited < self.poll_timeout:
            success, result = self.provider.auth_status(txid)
            if success:
                return True, {"Reply-Message": "Authenticated via Duo"}
            if result.get("status") != "waiting":
                return False, None
            sleep(self.poll_interval)
            waited += self.poll_interval

        logger.warning("%s: Duo push timed out", self.name)
        return False, None

    def test_connection(self) -> Tuple[bool, str]:
        ping_ok, ping_msg = self.provider.ping()
        if not ping_ok:
            return False, ping_msg
        return self.provider.check()
