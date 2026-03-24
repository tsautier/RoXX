"""
Duo Security MFA Provider for RoXX

Integrates with Duo Auth API v2 for push notifications,
passcodes, and phone-based MFA.

API Docs: https://duo.com/docs/authapi
"""

import hmac
import hashlib
import time
import email.utils
import urllib.parse
import logging
from typing import Tuple, Optional, Dict

import httpx

logger = logging.getLogger("roxx.auth.duo")


class DuoProvider:
    """
    Duo Security MFA integration via Auth API v2.
    
    Config required:
        - integration_key (ikey): Duo Integration Key
        - secret_key (skey): Duo Secret Key
        - api_hostname: Duo API hostname (e.g. api-XXXXXXXX.duosecurity.com)
    """

    def __init__(self, config: dict):
        self.ikey = config.get('integration_key', '')
        self.skey = config.get('secret_key', '')
        self.api_host = config.get('api_hostname', '')
        
        if not all([self.ikey, self.skey, self.api_host]):
            logger.error("[Duo] Missing required configuration (integration_key, secret_key, api_hostname)")

    def _sign_request(self, method: str, path: str, params: dict) -> dict:
        """
        Sign a Duo API request with HMAC-SHA1.
        Returns headers dict with Date and Authorization.
        """
        # RFC 2822 date
        now = email.utils.formatdate()

        # Canonicalize params
        canon_params = urllib.parse.urlencode(sorted(params.items()))

        # Build canonical string
        canon = "\n".join([now, method.upper(), self.api_host.lower(), path, canon_params])

        # HMAC-SHA1
        sig = hmac.new(
            self.skey.encode('utf-8'),
            canon.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()

        auth = f"{self.ikey}:{sig}"
        import base64
        auth_b64 = base64.b64encode(auth.encode('utf-8')).decode('utf-8')

        logger.debug(f"[Duo] Signed request: {method} {path}")

        return {
            "Date": now,
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def preauth(self, username: str) -> Tuple[bool, Dict]:
        """
        Pre-authentication check. Returns available factors for user.
        
        Returns:
            (success, result_dict) where result_dict contains 'result' and 'devices'
        """
        path = "/auth/v2/preauth"
        params = {"username": username}
        headers = self._sign_request("POST", path, params)

        try:
            url = f"https://{self.api_host}{path}"
            response = httpx.post(url, data=params, headers=headers, timeout=10)
            data = response.json()

            logger.debug(f"[Duo] preauth response for {username}: {data.get('stat')}")

            if data.get("stat") == "OK":
                return True, data.get("response", {})
            else:
                msg = data.get("message", "Unknown error")
                logger.warning(f"[Duo] preauth failed for {username}: {msg}")
                return False, {"error": msg}

        except Exception as e:
            logger.error(f"[Duo] preauth error: {e}")
            return False, {"error": str(e)}

    def auth(self, username: str, factor: str = "push", device: str = "auto", passcode: str = None) -> Tuple[bool, Dict]:
        """
        Authenticate user with Duo.
        
        Args:
            username: Username
            factor: 'push', 'passcode', 'phone', or 'sms'
            device: Device ID (default 'auto')
            passcode: Passcode for 'passcode' factor
            
        Returns:
            (success, result_dict)
        """
        path = "/auth/v2/auth"
        params = {
            "username": username,
            "factor": factor,
            "device": device,
        }

        if factor == "passcode" and passcode:
            params["passcode"] = passcode

        # For async (push), we may need to poll with /auth_status
        if factor == "push":
            params["async"] = "1"

        headers = self._sign_request("POST", path, params)

        try:
            url = f"https://{self.api_host}{path}"
            response = httpx.post(url, data=params, headers=headers, timeout=30)
            data = response.json()

            logger.debug(f"[Duo] auth response for {username}: {data.get('stat')}")

            if data.get("stat") == "OK":
                result = data.get("response", {})
                # For async push, result contains 'txid' for polling
                if factor == "push" and "txid" in result:
                    return True, {"txid": result["txid"], "status": "pending"}
                # For sync results
                if result.get("result") == "allow":
                    return True, result
                else:
                    return False, result
            else:
                return False, {"error": data.get("message", "Auth failed")}

        except Exception as e:
            logger.error(f"[Duo] auth error: {e}")
            return False, {"error": str(e)}

    def auth_status(self, txid: str) -> Tuple[bool, Dict]:
        """
        Check the status of an async auth (push notification).
        
        Args:
            txid: Transaction ID from auth() response
            
        Returns:
            (success, result_dict) with 'result' being 'allow', 'deny', or 'waiting'
        """
        path = "/auth/v2/auth_status"
        params = {"txid": txid}
        headers = self._sign_request("GET", path, params)

        try:
            url = f"https://{self.api_host}{path}"
            query_string = urllib.parse.urlencode(sorted(params.items()))
            response = httpx.get(f"{url}?{query_string}", headers=headers, timeout=10)
            data = response.json()

            logger.debug(f"[Duo] auth_status for txid={txid}: {data.get('stat')}")

            if data.get("stat") == "OK":
                result = data.get("response", {})
                if result.get("result") == "allow":
                    return True, result
                elif result.get("result") == "deny":
                    return False, result
                else:
                    # Still waiting
                    return False, {"status": "waiting", "status_msg": result.get("status_msg", "Waiting for response")}
            else:
                return False, {"error": data.get("message", "Status check failed")}

        except Exception as e:
            logger.error(f"[Duo] auth_status error: {e}")
            return False, {"error": str(e)}

    def ping(self) -> Tuple[bool, str]:
        """Test connectivity to Duo API"""
        path = "/auth/v2/ping"
        try:
            url = f"https://{self.api_host}{path}"
            response = httpx.get(url, timeout=5)
            data = response.json()

            if data.get("stat") == "OK":
                logger.debug(f"[Duo] Ping OK: {data.get('response', {}).get('time')}")
                return True, "Duo API reachable"
            return False, f"Duo API error: {data.get('message', 'Unknown')}"

        except Exception as e:
            logger.error(f"[Duo] Ping error: {e}")
            return False, f"Connection failed: {e}"

    def check(self) -> Tuple[bool, str]:
        """Verify API credentials are valid (requires signed request)"""
        path = "/auth/v2/check"
        params = {}
        headers = self._sign_request("GET", path, params)

        try:
            url = f"https://{self.api_host}{path}"
            response = httpx.get(url, headers=headers, timeout=5)
            data = response.json()

            if data.get("stat") == "OK":
                logger.debug("[Duo] Credential check OK")
                return True, "Duo credentials valid"
            return False, f"Invalid credentials: {data.get('message', 'Unknown')}"

        except Exception as e:
            logger.error(f"[Duo] Check error: {e}")
            return False, f"Check failed: {e}"
