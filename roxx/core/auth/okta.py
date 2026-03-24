"""
Okta MFA Provider for RoXX

Integrates with Okta Verify/Factor API for push-based and
TOTP-based MFA verification.

API Docs: https://developer.okta.com/docs/reference/api/factors/
"""

import logging
from typing import Tuple, Optional, Dict, List

import httpx

logger = logging.getLogger("roxx.auth.okta")


class OktaProvider:
    """
    Okta MFA integration via Factor API.
    
    Config required:
        - org_url: Okta org URL (e.g. https://dev-XXXXXXXX.okta.com)
        - api_token: Okta API token with factor management permissions
    """

    def __init__(self, config: dict):
        self.org_url = config.get('org_url', '').rstrip('/')
        self.api_token = config.get('api_token', '')

        if not all([self.org_url, self.api_token]):
            logger.error("[Okta] Missing required configuration (org_url, api_token)")

        self._headers = {
            "Authorization": f"SSWS {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_user_id(self, username: str) -> Optional[str]:
        """Resolve username to Okta user ID"""
        try:
            url = f"{self.org_url}/api/v1/users/{username}"
            response = httpx.get(url, headers=self._headers, timeout=10)

            if response.status_code == 200:
                user_id = response.json().get("id")
                logger.debug(f"[Okta] Resolved {username} -> {user_id}")
                return user_id
            else:
                logger.warning(f"[Okta] User {username} not found: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"[Okta] Error resolving user: {e}")
            return None

    def list_factors(self, username: str) -> Tuple[bool, List[Dict]]:
        """
        List enrolled MFA factors for a user.
        
        Returns:
            (success, list of factor dicts)
        """
        user_id = self._get_user_id(username)
        if not user_id:
            return False, []

        try:
            url = f"{self.org_url}/api/v1/users/{user_id}/factors"
            response = httpx.get(url, headers=self._headers, timeout=10)

            if response.status_code == 200:
                factors = response.json()
                logger.debug(f"[Okta] {username} has {len(factors)} factors enrolled")
                return True, factors
            else:
                logger.warning(f"[Okta] Failed to list factors: {response.status_code}")
                return False, []

        except Exception as e:
            logger.error(f"[Okta] Error listing factors: {e}")
            return False, []

    def verify_factor(self, username: str, factor_id: str, passcode: str = None) -> Tuple[bool, Dict]:
        """
        Verify an MFA factor (TOTP passcode or trigger push).
        
        Args:
            username: Okta username
            factor_id: Factor ID to verify against
            passcode: TOTP passcode (None for push factors)
            
        Returns:
            (success, result_dict)
        """
        user_id = self._get_user_id(username)
        if not user_id:
            return False, {"error": "User not found"}

        try:
            url = f"{self.org_url}/api/v1/users/{user_id}/factors/{factor_id}/verify"
            body = {}
            if passcode:
                body["passCode"] = passcode

            response = httpx.post(url, json=body, headers=self._headers, timeout=30)
            data = response.json()

            logger.debug(f"[Okta] verify_factor for {username}: status={response.status_code}")

            if response.status_code == 200:
                result = data.get("factorResult", "")
                if result == "SUCCESS":
                    return True, data
                elif result == "WAITING":
                    # Push notification sent, need to poll
                    poll_link = None
                    for link in data.get("_links", {}).get("poll", []):
                        poll_link = link.get("href")
                    return False, {"status": "waiting", "poll_url": poll_link, "factorResult": result}
                else:
                    return False, {"status": result, "error": data.get("factorResult", "Verification failed")}
            else:
                error_msg = data.get("errorSummary", f"HTTP {response.status_code}")
                logger.warning(f"[Okta] Factor verification failed: {error_msg}")
                return False, {"error": error_msg}

        except Exception as e:
            logger.error(f"[Okta] Error verifying factor: {e}")
            return False, {"error": str(e)}

    def poll_factor(self, poll_url: str) -> Tuple[bool, Dict]:
        """
        Poll for push notification result.
        
        Args:
            poll_url: URL from verify_factor 'WAITING' response
            
        Returns:
            (success, result_dict)
        """
        try:
            response = httpx.get(poll_url, headers=self._headers, timeout=10)
            data = response.json()

            result = data.get("factorResult", "")
            logger.debug(f"[Okta] Poll result: {result}")

            if result == "SUCCESS":
                return True, data
            elif result == "WAITING":
                return False, {"status": "waiting"}
            elif result in ("REJECTED", "TIMEOUT"):
                return False, {"status": result, "error": f"Factor {result.lower()}"}
            else:
                return False, {"status": result}

        except Exception as e:
            logger.error(f"[Okta] Poll error: {e}")
            return False, {"error": str(e)}

    def enroll_factor(self, username: str, factor_type: str = "token:software:totp", provider: str = "OKTA") -> Tuple[bool, Dict]:
        """
        Enroll a new MFA factor for a user.
        
        Args:
            username: Okta username
            factor_type: Factor type (e.g. 'token:software:totp', 'push')
            provider: Factor provider (e.g. 'OKTA', 'GOOGLE')
            
        Returns:
            (success, enrollment_data)
        """
        user_id = self._get_user_id(username)
        if not user_id:
            return False, {"error": "User not found"}

        try:
            url = f"{self.org_url}/api/v1/users/{user_id}/factors"
            body = {
                "factorType": factor_type,
                "provider": provider,
            }

            response = httpx.post(url, json=body, headers=self._headers, timeout=10)
            data = response.json()

            if response.status_code in (200, 201):
                logger.info(f"[Okta] Enrolled factor {factor_type} for {username}")
                return True, data
            else:
                error_msg = data.get("errorSummary", f"HTTP {response.status_code}")
                logger.warning(f"[Okta] Enrollment failed: {error_msg}")
                return False, {"error": error_msg}

        except Exception as e:
            logger.error(f"[Okta] Enrollment error: {e}")
            return False, {"error": str(e)}

    def test_connection(self) -> Tuple[bool, str]:
        """Test connectivity to Okta API"""
        try:
            url = f"{self.org_url}/api/v1/org"
            response = httpx.get(url, headers=self._headers, timeout=5)

            if response.status_code == 200:
                org = response.json()
                name = org.get("name", "Unknown")
                logger.debug(f"[Okta] Connection OK: {name}")
                return True, f"Connected to {name}"
            elif response.status_code == 401:
                return False, "Invalid API token"
            else:
                return False, f"HTTP {response.status_code}"

        except Exception as e:
            logger.error(f"[Okta] Connection test error: {e}")
            return False, f"Connection failed: {e}"
