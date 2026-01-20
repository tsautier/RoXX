import logging
import sqlite3
import re
import secrets
import bcrypt
from datetime import datetime
from roxx.core.auth.db import AdminDatabase

logger = logging.getLogger("roxx.auth")

class AuthManager:
    """
    Handles Admin Authentication, Password Hashing, and User Management.
    """

    @staticmethod
    def init():
        """Initialize Auth Subsystem"""
        AdminDatabase.init_db()
        # Ensure default admin exists if table is empty
        AuthManager._ensure_default_admin()

    @staticmethod
    def _ensure_default_admin():
        """Create default admin/admin account if no users exist"""
        conn = AdminDatabase.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM admins")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.warning("No admins found. Creating default 'admin' user.")
            # Default password 'admin' - MUST CHANGE on first login
            # Bcrypt hash
            pw_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO admins (username, password_hash, must_change_password)
                VALUES (?, ?, 1)
            """, ("admin", pw_hash))
            conn.commit()
        
        conn.close()

    @staticmethod
    def verify_credentials(username, password=None):
        """
        Verify username and password (or just existence for SSO).
        Returns:
           (success: bool, user_data: dict or None)
        """
        conn = AdminDatabase.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            logger.warning(f"User {username} not found")
            return False, None
            
        auth_source = user["auth_source"]
        
        # 1. Local Auth
        if auth_source == 'local':
            if not password:
                return False, None
            try:
                stored_hash = user["password_hash"].encode('utf-8')
                password_bytes = password.encode('utf-8')
                if not bcrypt.checkpw(password_bytes, stored_hash):
                    logger.warning(f"Password mismatch for {username}")
                    return False, None
            except Exception as e:
                logger.error(f"Password check failed: {e}")
                return False, None

        # 2. LDAP Auth
        elif auth_source == 'ldap':
            if not password:
                return False, None
            
            try:
                from roxx.core.auth.ldap import LdapProvider
                if LdapProvider.verify_credentials(username, password):
                    return True, dict(user)
                else:
                    logger.warning(f"LDAP verification failed for {username}")
                    return False, None
            except ImportError:
                 logger.error("ldap3 library not installed")
                 return False, None
            except Exception as e:
                 logger.error(f"LDAP Auth Error: {e}")
                 return False, None

        # 3. RADIUS Auth
        elif auth_source == 'radius':
            if not password:
                return False, None
            
            try:
                from roxx.core.auth.radius import RadiusProvider
                if RadiusProvider.verify_credentials(username, password):
                    return True, dict(user)
                else:
                    logger.warning(f"RADIUS verification failed for {username}")
                    return False, None
            except ImportError:
                 logger.error("pyrad library not installed")
                 return False, None
            except Exception as e:
                 logger.error(f"RADIUS Auth Error: {e}")
                 return False, None

        # 4. SAML Auth (No password check here, usually done via ACS)
        elif auth_source == 'saml':
             # SAML login is handled via /auth/saml/acs, not here usually.
             # If we are here, it might be a re-check or error.
             pass

        # Update last login
        try:
            conn = AdminDatabase.get_connection()
            conn.execute("UPDATE admins SET last_login = ? WHERE username = ?", (datetime.now(), username))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update last_login for {username}: {e}")

        return True, dict(user)

    @staticmethod
    def create_admin(username, password=None, auth_source='local', external_id=None):
        """Create a new admin user"""
        conn = AdminDatabase.get_connection()
        cursor = conn.cursor()
        
        try:
            pw_hash = None
            if auth_source == 'local' and password:
                pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO admins (username, password_hash, auth_source, external_id, must_change_password)
                VALUES (?, ?, ?, ?, ?)
            """, (username, pw_hash, auth_source, external_id, 1 if auth_source == 'local' else 0))
            conn.commit()
            return True, "User created"
        except sqlite3.IntegrityError:
            return False, "Username already exists"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    @staticmethod
    def list_admins():
        """List all admin users"""
        conn = AdminDatabase.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, auth_source, last_login FROM admins")
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users

    @staticmethod
    def delete_admin(username):
        """Delete an admin user"""
        if username == 'admin': # Prevent deleting default admin
             return False, "Cannot delete default admin"
             
        conn = AdminDatabase.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admins WHERE username = ?", (username,))
            conn.commit()
            return True, "User deleted"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()


    @staticmethod
    def check_password_complexity(password: str) -> tuple[bool, str]:
        """
        Enforce password complexity:
        - Min 12 chars
        - At least 1 uppercase
        - At least 1 lowercase
        - At least 1 digit or special char
        """
        if len(password) < 12:
            return False, "Password must be at least 12 characters long."
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter."

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter."

        if not re.search(r"\d|[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one number or special character."

        return True, ""

    @staticmethod
    def change_password(username, new_password):
        """
        Update password for a user.
        Enforces complexity.
        Resets 'must_change_password' flag.
        """
        is_valid, error = AuthManager.check_password_complexity(new_password)
        if not is_valid:
            raise ValueError(error)

        pw_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        logger.info(f"Changing password for {username}. New hash generated.")
        
        conn = AdminDatabase.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE admins 
            SET password_hash = ?, must_change_password = 0 
            WHERE username = ?
        """, (pw_hash, username))
        
        logger.info(f"Updated password for {username}. Rows affected: {cursor.rowcount}")
        logger.info(f"New Hash stored: {pw_hash[:10]}...")
        
        conn.commit()
        conn.close()
    @staticmethod
    def setup_mfa(username):
        """
        Generate a new TOTP secret for MFA setup.
        Returns: (secret_base32, provisioning_uri)
        """
        # Generate random 160-bit (20 bytes) secret encoded as Base32
        # Standard: 16 bytes = 128 bit minimal, 20 bytes = 160 bits (recommended)
        import base64
        secret_bytes = secrets.token_bytes(20)
        secret_base32 = base64.b32encode(secret_bytes).decode('utf-8').strip('=')
        
        # Provisioning URI for QR Code
        # otpauth://totp/RoXX:admin?secret=...&issuer=RoXX
        provisioning_uri = f"otpauth://totp/RoXX:{username}?secret={secret_base32}&issuer=RoXX"
        return secret_base32, provisioning_uri

    @staticmethod
    def verify_mfa(username, token, pending_secret=None):
        """
        Verify a TOTP token. 
        If pending_secret is provided (during setup), verify against that.
        Otherwise verify against the stored secret in DB.
        """
        secret = pending_secret
        if not secret:
            # Fetch from DB
            conn = AdminDatabase.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT mfa_secret FROM admins WHERE username = ?", (username,))
            row = cursor.fetchone()
            conn.close()
            
            if row and row['mfa_secret']:
                secret = row['mfa_secret']
        
        if not secret:
            return False

        try:
            from roxx.core.auth.totp import TOTPAuthenticator
            # TOTPAuthenticator expects Base32 string
            auth = TOTPAuthenticator(secret=secret)
            return auth.verify(token)
        except Exception as e:
            logger.error(f"MFA Verification Error: {e}")
            return False

    @staticmethod
    def enable_mfa(username, secret):
        """
        Save the confirmed MFA secret to the database.
        """
        # Final verification that secret is valid? (Caller should have verified with a token)
        conn = AdminDatabase.get_connection()
        conn.execute("UPDATE admins SET mfa_secret = ? WHERE username = ?", (secret, username))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def disable_mfa(username):
        """
        Disable MFA for a user.
        """
        conn = AdminDatabase.get_connection()
        conn.execute("UPDATE admins SET mfa_secret = NULL WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        return True
