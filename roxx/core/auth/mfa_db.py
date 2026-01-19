"""
MFA Database Management
Handles MFA settings storage and retrieval
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from .mfa import MFAManager


DB_PATH = Path.home() / ".roxx" / "mfa.db"
db_conn = None


class MFADatabase:
    """Database operations for MFA settings"""
    
    @staticmethod
    def init():
        """Initialize MFA database"""
        global db_conn
        
        # Ensure directory exists
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            db_conn.row_factory = sqlite3.Row
            cursor = db_conn.cursor()
            
            # Create MFA settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_mfa (
                    username TEXT PRIMARY KEY,
                    mfa_enabled BOOLEAN DEFAULT 0,
                    mfa_type TEXT,
                    totp_secret TEXT,
                    phone_number TEXT,
                    backup_codes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            ''')
            
            db_conn.commit()
            print("[MFA] Database initialized")
            
        except Exception as e:
            print(f"[MFA] Failed to initialize database: {e}")
            raise
    
    @staticmethod
    def enroll_totp(username: str, secret: str, backup_codes: List[str]) -> Tuple[bool, str]:
        """
        Enroll user in TOTP MFA
        
        Args:
            username: User's username
            secret: TOTP secret
            backup_codes: List of hashed backup codes
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cursor = db_conn.cursor()
            
            # Store backup codes as JSON
            backup_codes_json = json.dumps(backup_codes)
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_mfa 
                (username, mfa_enabled, mfa_type, totp_secret, backup_codes, created_at)
                VALUES (?, 1, 'totp', ?, ?, CURRENT_TIMESTAMP)
            ''', (username, secret, backup_codes_json))
            
            db_conn.commit()
            return True, "MFA enrolled successfully"
            
        except Exception as e:
            return False, f"Failed to enroll MFA: {e}"
    
    @staticmethod
    def get_mfa_settings(username: str) -> Optional[Dict]:
        """
        Get MFA settings for user
        
        Args:
            username: User's username
            
        Returns:
            Dictionary with MFA settings or None
        """
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                'SELECT * FROM user_mfa WHERE username = ?',
                (username,)
            )
            row = cursor.fetchone()
            
            if row:
                settings = dict(row)
                # Parse backup codes from JSON
                if settings.get('backup_codes'):
                    settings['backup_codes'] = json.loads(settings['backup_codes'])
                return settings
            return None
            
        except Exception as e:
            print(f"[MFA] Error getting settings: {e}")
            return None
    
    @staticmethod
    def is_mfa_enabled(username: str) -> bool:
        """Check if MFA is enabled for user"""
        settings = MFADatabase.get_mfa_settings(username)
        return settings and settings.get('mfa_enabled', False)
    
    @staticmethod
    def verify_and_consume_backup_code(username: str, code: str) -> Tuple[bool, str]:
        """
        Verify backup code and remove it from available codes
        
        Args:
            username: User's username
            code: Backup code from user
            
        Returns:
            Tuple of (success, message)
        """
        try:
            settings = MFADatabase.get_mfa_settings(username)
            if not settings:
                return False, "MFA not enrolled"
            
            backup_codes = settings.get('backup_codes', [])
            
            # Verify code
            is_valid, matched_hash = MFAManager.verify_backup_code(code, backup_codes)
            
            if not is_valid:
                return False, "Invalid backup code"
            
            # Remove used code
            backup_codes.remove(matched_hash)
            
            # Update database
            cursor = db_conn.cursor()
            cursor.execute('''
                UPDATE user_mfa 
                SET backup_codes = ?, last_used = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (json.dumps(backup_codes), username))
            
            db_conn.commit()
            
            remaining = len(backup_codes)
            return True, f"Backup code accepted. {remaining} codes remaining."
            
        except Exception as e:
            return False, f"Error verifying backup code: {e}"
    
    @staticmethod
    def update_last_used(username: str):
        """Update last used timestamp"""
        try:
            cursor = db_conn.cursor()
            cursor.execute('''
                UPDATE user_mfa 
                SET last_used = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (username,))
            db_conn.commit()
        except Exception as e:
            print(f"[MFA] Error updating last used: {e}")
    
    @staticmethod
    def disable_mfa(username: str) -> Tuple[bool, str]:
        """
        Disable MFA for user
        
        Args:
            username: User's username
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cursor = db_conn.cursor()
            cursor.execute('''
                UPDATE user_mfa 
                SET mfa_enabled = 0
                WHERE username = ?
            ''', (username,))
            
            db_conn.commit()
            
            if cursor.rowcount > 0:
                return True, "MFA disabled successfully"
            return False, "User not found"
            
        except Exception as e:
            return False, f"Failed to disable MFA: {e}"
    
    @staticmethod
    def delete_mfa(username: str) -> Tuple[bool, str]:
        """
        Completely remove MFA settings for user
        
        Args:
            username: User's username
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cursor = db_conn.cursor()
            cursor.execute('DELETE FROM user_mfa WHERE username = ?', (username,))
            db_conn.commit()
            
            if cursor.rowcount > 0:
                return True, "MFA settings deleted"
            return False, "User not found"
            
        except Exception as e:
            return False, f"Failed to delete MFA: {e}"
    
    @staticmethod
    def list_mfa_users() -> List[Dict]:
        """Get list of all users with MFA"""
        try:
            cursor = db_conn.cursor()
            cursor.execute('''
                SELECT username, mfa_enabled, mfa_type, created_at, last_used
                FROM user_mfa
                ORDER BY created_at DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"[MFA] Error listing users: {e}")
            return []
