import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("roxx.auth.config")

class AuthProviderDatabase:
    """
    Database for storing authentication provider configurations.
    Supports LDAP, SAML, and RADIUS providers with multiple instances.
    """
    
    @staticmethod
    def get_db_path():
        """Get path to auth provider config database"""
        db_dir = Path.home() / ".roxx"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "auth_providers.db"
    
    @staticmethod
    def get_connection():
        """Get database connection"""
        db_path = AuthProviderDatabase.get_db_path()
        conn = sqlite3.connect(str(db_path))
        return conn
    
    @staticmethod
    def init_db():
        """Initialize auth provider database with schema"""
        conn = AuthProviderDatabase.get_connection()
        cursor = conn.cursor()
        
        # Create auth_providers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_type TEXT NOT NULL CHECK(provider_type IN ('ldap', 'saml', 'radius')),
                name TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                config_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider_type, name)
            )
        """)
        
        # Create index on provider_type and enabled for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider_type_enabled 
            ON auth_providers(provider_type, enabled)
        """)
        
        conn.commit()
        conn.close()
        logger.info("Auth provider database initialized")


class ConfigManager:
    """
    Manager for authentication provider configurations.
    Handles CRUD operations and configuration retrieval.
    """
    
    @staticmethod
    def init():
        """Initialize configuration system"""
        AuthProviderDatabase.init_db()
    
    @staticmethod
    def list_providers(provider_type=None, enabled_only=False):
        """
        List all authentication providers.
        
        Args:
            provider_type: Filter by type ('ldap', 'saml', 'radius'). None = all types.
            enabled_only: If True, only return enabled providers.
            
        Returns:
            List of provider dicts with parsed config_json
        """
        conn = AuthProviderDatabase.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM auth_providers WHERE 1=1"
        params = []
        
        if provider_type:
            query += " AND provider_type = ?"
            params.append(provider_type)
        
        if enabled_only:
            query += " AND enabled = 1"
        
        query += " ORDER BY provider_type, name"
        
        cursor.execute(query, params)
        providers = []
        
        for row in cursor.fetchall():
            provider = dict(row)
            # Parse config JSON
            provider['config'] = json.loads(provider['config_json'])
            del provider['config_json']  # Remove raw JSON from output
            providers.append(provider)
        
        conn.close()
        return providers
    
    @staticmethod
    def get_provider(provider_id):
        """Get a specific provider by ID"""
        conn = AuthProviderDatabase.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM auth_providers WHERE id = ?", (provider_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        provider = dict(row)
        provider['config'] = json.loads(provider['config_json'])
        del provider['config_json']
        return provider
    
    @staticmethod
    def get_active_provider(provider_type):
        """
        Get the first enabled provider of a given type.
        Used for authentication when multiple providers exist.
        
        Returns:
            Provider dict with config, or None if no enabled provider found.
        """
        providers = ConfigManager.list_providers(
            provider_type=provider_type,
            enabled_only=True
        )
        return providers[0] if providers else None
    
    @staticmethod
    def create_provider(provider_type, name, config_dict, enabled=True):
        """
        Create a new authentication provider.
        
        Args:
            provider_type: 'ldap', 'saml', or 'radius'
            name: Display name for the provider
            config_dict: Provider-specific configuration dictionary
            enabled: Whether provider is active
            
        Returns:
            (success: bool, message: str, provider_id: int or None)
        """
        if provider_type not in ['ldap', 'saml', 'radius']:
            return False, "Invalid provider type", None
        
        # Validate config has required fields
        valid, error = ConfigManager._validate_config(provider_type, config_dict)
        if not valid:
            return False, error, None
        
        conn = AuthProviderDatabase.get_connection()
        cursor = conn.cursor()
        
        try:
            config_json = json.dumps(config_dict)
            cursor.execute("""
                INSERT INTO auth_providers (provider_type, name, enabled, config_json)
                VALUES (?, ?, ?, ?)
            """, (provider_type, name, enabled, config_json))
            
            provider_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Created {provider_type} provider: {name} (ID: {provider_id})")
            return True, "Provider created successfully", provider_id
            
        except sqlite3.IntegrityError:
            return False, f"Provider '{name}' already exists for {provider_type}", None
        except Exception as e:
            logger.error(f"Error creating provider: {e}")
            return False, str(e), None
        finally:
            conn.close()
    
    @staticmethod
    def update_provider(provider_id, name=None, config_dict=None, enabled=None):
        """
        Update an existing provider.
        
        Args:
            provider_id: Provider ID to update
            name: New name (optional)
            config_dict: New configuration (optional)
            enabled: New enabled status (optional)
            
        Returns:
            (success: bool, message: str)
        """
        provider = ConfigManager.get_provider(provider_id)
        if not provider:
            return False, "Provider not found"
        
        # Validate new config if provided
        if config_dict is not None:
            valid, error = ConfigManager._validate_config(provider['provider_type'], config_dict)
            if not valid:
                return False, error
        
        conn = AuthProviderDatabase.get_connection()
        cursor = conn.cursor()
        
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            
            if config_dict is not None:
                updates.append("config_json = ?")
                params.append(json.dumps(config_dict))
            
            if enabled is not None:
                updates.append("enabled = ?")
                params.append(enabled)
            
            updates.append("updated_at = ?")
            params.append(datetime.now())
            
            params.append(provider_id)
            
            query = f"UPDATE auth_providers SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            
            logger.info(f"Updated provider ID {provider_id}")
            return True, "Provider updated successfully"
            
        except sqlite3.IntegrityError:
            return False, f"Provider name '{name}' already exists"
        except Exception as e:
            logger.error(f"Error updating provider: {e}")
            return False, str(e)
        finally:
            conn.close()
    
    @staticmethod
    def delete_provider(provider_id):
        """Delete a provider"""
        conn = AuthProviderDatabase.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM auth_providers WHERE id = ?", (provider_id,))
            if cursor.rowcount == 0:
                return False, "Provider not found"
            
            conn.commit()
            logger.info(f"Deleted provider ID {provider_id}")
            return True, "Provider deleted successfully"
            
        except Exception as e:
            logger.error(f"Error deleting provider: {e}")
            return False, str(e)
        finally:
            conn.close()
    
    @staticmethod
    def _validate_config(provider_type, config_dict):
        """
        Validate provider configuration has required fields.
        
        Returns:
            (valid: bool, error_message: str)
        """
        if provider_type == 'ldap':
            required = ['server', 'bind_dn_format']
            for field in required:
                if field not in config_dict or not config_dict[field]:
                    return False, f"Missing required field: {field}"
        
        elif provider_type == 'saml':
            required = ['idp_entity_id', 'idp_sso_url', 'idp_x509_cert', 'sp_entity_id']
            for field in required:
                if field not in config_dict or not config_dict[field]:
                    return False, f"Missing required field: {field}"
        
        elif provider_type == 'radius':
            required = ['server', 'port', 'secret']
            for field in required:
                if field not in config_dict or not config_dict[field]:
                    return False, f"Missing required field: {field}"
            
            # Validate port is numeric
            try:
                port = int(config_dict['port'])
                if port < 1 or port > 65535:
                    return False, "Port must be between 1 and 65535"
            except ValueError:
                return False, "Port must be a number"
        
        return True, ""
    
    @staticmethod
    def test_provider(provider_type, config_dict, test_username, test_password):
        """
        Test provider configuration without saving.
        
        Args:
            provider_type: 'ldap', 'saml', or 'radius'
            config_dict: Provider configuration
            test_username: Test username
            test_password: Test password
            
        Returns:
            (success: bool, message: str)
        """
        # Validate config first
        valid, error = ConfigManager._validate_config(provider_type, config_dict)
        if not valid:
            return False, f"Configuration validation failed: {error}"
        
        try:
            if provider_type == 'ldap':
                from roxx.core.auth.ldap import LdapProvider
                result = LdapProvider.test_connection(config_dict, test_username, test_password)
                return result, "LDAP connection successful" if result else "LDAP connection failed"
            
            elif provider_type == 'radius':
                from roxx.core.auth.radius import RadiusProvider
                result = RadiusProvider.test_connection(config_dict, test_username, test_password)
                return result, "RADIUS authentication successful" if result else "RADIUS authentication failed"
            
            elif provider_type == 'saml':
                # SAML testing is more complex, just validate config for now
                return True, "SAML configuration validated (full test requires IdP interaction)"
        
        except ImportError as e:
            return False, f"Provider module not available: {e}"
        except Exception as e:
            logger.error(f"Provider test error: {e}")
            return False, f"Test failed: {str(e)}"
