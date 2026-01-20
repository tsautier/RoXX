"""
SMS Gateway Provider for MFA
Supports:
1. Twilio
2. Generic HTTP POST (for custom getaways)
"""
import logging
import httpx
import json

logger = logging.getLogger("roxx.auth.sms")

class SMSProvider:
    @staticmethod
    async def send_sms(phone_number: str, message: str, config: dict) -> bool:
        """
        Send SMS using the configured provider.
        config format:
        {
            "provider": "twilio" | "generic",
            "twilio_sid": "...",
            "twilio_token": "...",
            "twilio_from": "...",
            "generic_url": "...",
            "generic_headers": {...},
            "generic_body_template": "..."  # JSON string or template
        }
        """
        provider = config.get("provider", "").lower()
        
        try:
            if provider == "twilio":
                return await SMSProvider._send_twilio(phone_number, message, config)
            elif provider == "generic":
                return await SMSProvider._send_generic(phone_number, message, config)
            else:
                logger.error(f"Unknown SMS provider: {provider}")
                return False
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {e}")
            return False

    @staticmethod
    async def _send_twilio(phone_number: str, message: str, config: dict) -> bool:
        sid = config.get("twilio_sid")
        token = config.get("twilio_token")
        from_number = config.get("twilio_from")
        
        if not sid or not token or not from_number:
            logger.error("Missing Twilio credentials")
            return False
            
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        
        data = {
            "To": phone_number,
            "From": from_number,
            "Body": message
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data, auth=(sid, token))
            
            if resp.status_code in (200, 201):
                return True
            else:
                logger.error(f"Twilio API Error: {resp.text}")
                return False

    @staticmethod
    async def _send_generic(phone_number: str, message: str, config: dict) -> bool:
        url = config.get("generic_url")
        if not url:
            return False
            
        headers = config.get("generic_headers", {})
        if isinstance(headers, str):
            try: headers = json.loads(headers)
            except: pass
            
        body_template = config.get("generic_body_template", "{}")
        
        # Simple templating
        # Replace {phone} and {message} in the body
        # This assumes body is meant to be JSON
        
        # Check if we should send as JSON or Form
        # For now assume JSON body logic
        payload_str = body_template.replace("{phone}", phone_number).replace("{message}", message)
        
        try:
            payload = json.loads(payload_str)
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers)
                return resp.status_code >= 200 and resp.status_code < 300
        except json.JSONDecodeError:
            # Maybe it's form data? Or just send as string logic?
            # For MVP, support JSON replacements
            logger.error("Generic SMS: Body template must be valid JSON after substitution")
            return False
