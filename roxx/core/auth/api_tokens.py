"""
API Token Management

Provides secure API key authentication for REST API access.
Uses bcrypt-hashed tokens stored in SQLite database.
"""

import sqlite3
import secrets
import bcrypt
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

logger = logging.getLogger("roxx.api_tokens")

# Database path
DB_PATH = Path.home() / ".roxx" / "api_tokens.db"


class APITokenManager:
    """
    Manages API tokens for authentication.
    
    Tokens are:
    - Generated with secrets.token_urlsafe(32) - 256 bits of entropy
    - Stored hashed with bcrypt
    - Associated with a name/description
    - Revocable
    """
    
    @staticmethod
    def init():
        """Initialize API tokens database"""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    token_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    enabled BOOLEAN DEFAULT 1
                )
            """)
            conn.commit()
            logger.info(f"API tokens database initialized at {DB_PATH}")
    
    @staticmethod
    def generate_token(name: str) -> Tuple[bool, str, Optional[str]]:
        """
        Generate a new API token.
        
        Args:
            name: Descriptive name for the token
        
        Returns:
            (success: bool, message: str, token: str or None)
            
        Note: The raw token is returned ONCE and should be shown to user.
              It cannot be retrieved later.
        """
        try:
            # Generate secure random token (43 chars, 256 bits)
            raw_token = secrets.token_urlsafe(32)
            
            # Hash token for storage
            token_hash = bcrypt.hashpw(raw_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO api_tokens (name, token_hash) VALUES (?, ?)",
                    (name, token_hash)
                )
                conn.commit()
            
            logger.info(f"Generated API token: {name}")
            return True, f"Token created: {name}", raw_token
            
        except sqlite3.IntegrityError:
            return False, f"Token with name '{name}' already exists", None
        except Exception as e:
            logger.error(f"Error generating token: {e}")
            return False, f"Error: {str(e)}", None
    
    @staticmethod
    def verify_token(raw_token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify an API token.
        
        Args:
            raw_token: The raw token string to verify
        
        Returns:
            (valid: bool, token_name: str or None)
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get all enabled tokens
                rows = conn.execute(
                    "SELECT id, name, token_hash FROM api_tokens WHERE enabled = 1"
                ).fetchall()
                
                for row in rows:
                    # Check if token matches
                    if bcrypt.checkpw(raw_token.encode('utf-8'), row['token_hash'].encode('utf-8')):
                        # Update last_used timestamp
                        conn.execute(
                            "UPDATE api_tokens SET last_used = CURRENT_TIMESTAMP WHERE id = ?",
                            (row['id'],)
                        )
                        conn.commit()
                        
                        logger.debug(f"API token verified: {row['name']}")
                        return True, row['name']
            
            # No match found
            logger.warning("Invalid API token attempt")
            return False, None
            
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return False, None
    
    @staticmethod
    def list_tokens() -> List[dict]:
        """
        List all API tokens (without revealing the actual tokens).
        
        Returns:
            List of token info dictionaries
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                
                rows = conn.execute("""
                    SELECT id, name, created_at, last_used, enabled
                    FROM api_tokens
                    ORDER BY created_at DESC
                """).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error listing tokens: {e}")
            return []
    
    @staticmethod
    def revoke_token(token_id: int) -> Tuple[bool, str]:
        """
        Revoke (disable) an API token.
        
        Args:
            token_id: ID of token to revoke
        
        Returns:
            (success: bool, message: str)
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "UPDATE api_tokens SET enabled = 0 WHERE id = ?",
                    (token_id,)
                )
                conn.commit()
                
                if conn.total_changes > 0:
                    logger.info(f"Revoked API token ID: {token_id}")
                    return True, "Token revoked successfully"
                else:
                    return False, "Token not found"
                    
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def delete_token(token_id: int) -> Tuple[bool, str]:
        """
        Permanently delete an API token.
        
        Args:
            token_id: ID of token to delete
        
        Returns:
            (success: bool, message: str)
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("DELETE FROM api_tokens WHERE id = ?", (token_id,))
                conn.commit()
                
                if conn.total_changes > 0:
                    logger.info(f"Deleted API token ID: {token_id}")
                    return True, "Token deleted successfully"
                else:
                    return False, "Token not found"
                    
        except Exception as e:
            logger.error(f"Error deleting token: {e}")
            return False, f"Error: {str(e)}"
