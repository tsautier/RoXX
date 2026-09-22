import logging
import os
import sqlite3
import re
import secrets
import bcrypt
from datetime import UTC, datetime
from pathlib import Path
from roxx.core.auth.db import AdminDatabase

logger = logging.getLogger("roxx.auth")

INITIAL_ADMIN_CREDENTIALS_FILENAME = "initial-admin-credentials.txt"

class AuthManager:
    """
    Handles Admin Authentication, Password Hashing, and User Management.
    """

    @staticmethod
    def init():
        """Initialize Auth Subsystem"""
        AdminDatabase.init_db()
        AuthManager._ensure_initial_admin()

    @staticmethod
    def get_initial_credentials_path() -> Path:
        """Return the protected file used to deliver generated bootstrap credentials."""
        return AdminDatabase.get_db_path().parent / INITIAL_ADMIN_CREDENTIALS_FILENAME

    @staticmethod
    def _write_initial_credentials(username: str, password: str) -> Path:
        """Write generated credentials with owner-only permissions where supported."""
        path = AuthManager.get_initial_credentials_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            "RoXX initial administrator credentials\n"
            f"Username: {username}\n"
            f"Password: {password}\n\n"
            "Sign in and change this password immediately. "
            "This file is deleted after password rotation.\n"
        )
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        if os.name != "nt":
            path.chmod(0o600)
        return path

    @staticmethod
    def _remove_initial_credentials(username: str) -> None:
        """Remove the bootstrap credential file after the matching account rotates it."""
        path = AuthManager.get_initial_credentials_path()
        if not path.exists():
            return
        try:
            content = path.read_text(encoding="utf-8")
            if f"Username: {username}\n" in content:
                path.unlink()
        except OSError as exc:
            logger.warning("Could not remove initial administrator credentials: %s", exc)

    @staticmethod
    def _new_initial_password() -> str:
        """Generate a high-entropy password that also satisfies the local policy."""
        return f"RoXX1!{secrets.token_urlsafe(24)}"

    @staticmethod
    def _ensure_initial_admin():
        """Create or migrate the initial administrator without a shared default password."""
        conn = AdminDatabase.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            count = cursor.execute("SELECT count(*) FROM admins").fetchone()[0]

            if count == 0:
                username = os.getenv("ROXX_BOOTSTRAP_ADMIN_USERNAME", "admin").strip()
                supplied_password = os.getenv("ROXX_BOOTSTRAP_ADMIN_PASSWORD")
                if not username or "\n" in username or "\r" in username:
                    raise ValueError("ROXX_BOOTSTRAP_ADMIN_USERNAME is invalid")
                password = supplied_password or AuthManager._new_initial_password()
                valid, error = AuthManager.check_password_complexity(password)
                if not valid:
                    raise ValueError(f"ROXX_BOOTSTRAP_ADMIN_PASSWORD: {error}")

                pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
                    "utf-8"
                )
                cursor.execute("""
                    INSERT INTO admins (username, password_hash, must_change_password, role)
                    VALUES (?, ?, 1, 'superadmin')
                """, (username, pw_hash))
                if supplied_password is None:
                    path = AuthManager._write_initial_credentials(username, password)
                    logger.warning(
                        "Initial administrator created. Credentials are available in %s "
                        "until the password is changed.", path
                    )
                else:
                    logger.warning(
                        "Initial administrator created from ROXX_BOOTSTRAP_ADMIN_PASSWORD; "
                        "password rotation is required at first sign-in."
                    )
            else:
                row = cursor.execute("""
                    SELECT username, password_hash, auth_source, must_change_password
                    FROM admins WHERE username = 'admin'
                """).fetchone()
                if (
                    row
                    and row[2] == "local"
                    and row[3]
                    and row[1]
                    and bcrypt.checkpw(b"admin", row[1].encode("utf-8"))
                ):
                    password = AuthManager._new_initial_password()
                    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
                        "utf-8"
                    )
                    cursor.execute(
                        "UPDATE admins SET password_hash = ? WHERE username = 'admin'",
                        (pw_hash,),
                    )
                    path = AuthManager._write_initial_credentials("admin", password)
                    logger.warning(
                        "Legacy admin/admin credentials were disabled. Replacement credentials "
                        "are available in %s until the password is changed.", path
                    )

                cursor.execute("""
                    UPDATE admins SET role = 'superadmin'
                    WHERE username = 'admin' AND (role IS NULL OR role = 'admin')
                """)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
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

        # 4. SAML Auth is accepted only by the validated ACS flow.
        elif auth_source == 'saml':
             logger.warning(f"Rejected password login for SAML user {username}")
             return False, None
        else:
             logger.error(f"Unsupported authentication source for {username}: {auth_source}")
             return False, None

        # Update last login
        try:
            conn = AdminDatabase.get_connection()
            conn.execute(
                "UPDATE admins SET last_login = ? WHERE username = ?",
                (datetime.now(UTC).isoformat(), username),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update last_login for {username}: {e}")

        return True, dict(user)

    @staticmethod
    def get_auth_source(username: str) -> str | None:
        """Return the configured authentication source without authenticating the user."""
        conn = AdminDatabase.get_connection()
        try:
            row = conn.execute(
                "SELECT auth_source FROM admins WHERE username = ?", (username,)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    @staticmethod
    def create_admin(username, password=None, auth_source='local', external_id=None, role='admin'):
        """Create a new admin user"""
        conn = AdminDatabase.get_connection()
        cursor = conn.cursor()
        
        try:
            pw_hash = None
            if auth_source == 'local' and password:
                pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO admins (username, password_hash, auth_source, external_id, must_change_password, role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, pw_hash, auth_source, external_id, 1 if auth_source == 'local' else 0, role))
            conn.commit()
            logger.debug(f"[RBAC] Created admin {username} with role={role}")
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
        cursor.execute("SELECT username, email, auth_source, last_login, role FROM admins")
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
        AuthManager._remove_initial_credentials(username)
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
