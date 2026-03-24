"""
Okta Verify RADIUS authentication backend.
"""

from time import sleep
from typing import Dict, Optional, Tuple
import logging

from roxx.core.auth.okta import OktaProvider
from .base import RadiusBackend

logger = logging.getLogger("roxx.radius_backends.okta")


class OktaRadiusBackend(RadiusBackend):
    """
    Okta-backed authentication for RADIUS users.

    Configuration options:
    - org_url: Okta organization URL
    - api_token: Okta API token
    - factor_id: specific factor to verify (optional)
    - factor_type: factor type to select automatically (default: push)
    - provider: factor provider filter (default: OKTA)
    - poll_interval: seconds between push status checks
    - poll_timeout: max seconds to wait for approval
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.factor_id = config.get("factor_id", "")
        self.factor_type = config.get("factor_type", "push")
        self.provider_name = config.get("provider", "OKTA")
        self.poll_interval = int(config.get("poll_interval", 2))
        self.poll_timeout = int(config.get("poll_timeout", 30))
        self.provider = OktaProvider(config)

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        if not username:
            return False, None

        factor_id = self.factor_id or self._resolve_factor_id(username)
        if not factor_id:
            logger.warning("%s: No matching Okta factor for %s", self.name, username)
            return False, None

        passcode = password if self.factor_type != "push" else None
        success, result = self.provider.verify_factor(username, factor_id, passcode)
        if success:
            return True, {"Reply-Message": "Authenticated via Okta"}

        if result.get("status") == "waiting" and result.get("poll_url"):
            return self._poll_result(result["poll_url"])

        return False, None

    def _resolve_factor_id(self, username: str) -> Optional[str]:
        success, factors = self.provider.list_factors(username)
        if not success:
            return None

        for factor in factors:
            if factor.get("factorType") != self.factor_type:
                continue
            if factor.get("provider") != self.provider_name:
                continue
            return factor.get("id")
        return None

    def _poll_result(self, poll_url: str) -> Tuple[bool, Optional[Dict]]:
        waited = 0
        while waited < self.poll_timeout:
            success, result = self.provider.poll_factor(poll_url)
            if success:
                return True, {"Reply-Message": "Authenticated via Okta"}
            if result.get("status") != "waiting":
                return False, None
            sleep(self.poll_interval)
            waited += self.poll_interval

        logger.warning("%s: Okta push timed out", self.name)
        return False, None

    def test_connection(self) -> Tuple[bool, str]:
        return self.provider.test_connection()
