"""
Email OTP Provider
Supports SMTP for sending OTP codes.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

logger = logging.getLogger("roxx.auth.email")

class EmailProvider:
    @staticmethod
    async def send_email(to_email: str, subject: str, body: str, config: dict) -> bool:
        """
        Send Email using SMTP.
        config format:
        {
            "enabled": bool,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "...",
            "smtp_password": "...",
            "from_email": "...",
            "use_tls": bool
        }
        """
        if not config.get("enabled"):
            logger.warning("Email provider is disabled")
            return False

        smtp_server = config.get("smtp_server")
        smtp_port = int(config.get("smtp_port", 587))
        smtp_user = config.get("smtp_user")
        smtp_password = config.get("smtp_password")
        from_email = config.get("from_email")
        use_tls = config.get("use_tls", True)

        try:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # Synchronous SMTP (blocking), could be offloaded to background task/thread
            # For MVP, synchronous valid.
            
            context = ssl.create_default_context() if use_tls else None
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls(context=context)
                
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                
                server.sendmail(from_email, to_email, msg.as_string())
                
            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
