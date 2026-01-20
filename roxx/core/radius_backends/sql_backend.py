"""
SQL RADIUS Authentication Backend

Supports MySQL and PostgreSQL databases for RADIUS user authentication.
Includes connection pooling, multiple password hash support, and attribute mapping.
"""

from typing import Tuple, Dict, Optional
import logging
import hashlib
import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from .base import RadiusBackend

logger = logging.getLogger("roxx.radius_backends.sql")


class SqlRadiusBackend(RadiusBackend):
    """
    SQL authentication backend for RADIUS users.
    
    Configuration options:
    - db_type: 'mysql' or 'postgresql'
    - host: Database host
    - port: Database port
    - database: Database name
    - username: DB username
    - password: DB password
    - users_table: Table name for users (default: radusers)
    - username_column: Column for username (default: username)
    - password_column: Column for password hash (default: password)
    - password_type: Hash type ('bcrypt', 'sha256', 'md5', 'sha1', 'plain')
    - attributes_table: Optional table for user attributes
    - pool_size: Connection pool size (default: 5)
    - max_overflow: Max overflow connections (default: 10)
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        self.db_type = config.get('db_type', 'mysql')
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 3306 if self.db_type == 'mysql' else 5432)
        self.database = config.get('database')
        self.db_username = config.get('username')
        self.db_password = config.get('password')
        
        self.users_table = config.get('users_table', 'radusers')
        self.username_column = config.get('username_column', 'username')
        self.password_column = config.get('password_column', 'password')
        self.password_type = config.get('password_type', 'bcrypt')
        self.attributes_table = config.get('attributes_table')
        
        pool_size = config.get('pool_size', 5)
        max_overflow = config.get('max_overflow', 10)
        
        # Create database engine with connection pooling
        self.engine = self._create_engine(pool_size, max_overflow)
    
    def _create_engine(self, pool_size: int, max_overflow: int):
        """Create SQLAlchemy engine with connection pooling"""
        if self.db_type == 'mysql':
            connection_string = (
                f"mysql+mysqlconnector://{self.db_username}:{self.db_password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        elif self.db_type == 'postgresql':
            connection_string = (
                f"postgresql+psycopg2://{self.db_username}:{self.db_password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        
        return create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600  # Recycle connections after 1 hour
        )
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate user against SQL database.
        
        Returns:
            (success, radius_attributes)
        """
        if not username or not password:
            logger.warning("Empty username or password")
            return False, None
        
        try:
            with self.engine.connect() as conn:
                # Query user
                query = text(f"""
                    SELECT {self.password_column}
                    FROM {self.users_table}
                    WHERE {self.username_column} = :username
                """)
                
                result = conn.execute(query, {"username": username}).fetchone()
                
                if not result:
                    logger.warning(f"{self.name}: User {username} not found")
                    return False, None
                
                stored_password = result[0]
                
                # Verify password based on type
                if self._verify_password(password, stored_password):
                    logger.info(f"{self.name}: Authentication successful for {username}")
                    
                    # Get user attributes if attributes table is configured
                    radius_attrs = {}
                    if self.attributes_table:
                        radius_attrs = self._get_user_attributes_from_db(conn, username)
                    
                    return True, radius_attrs
                else:
                    logger.warning(f"{self.name}: Password verification failed for {username}")
                    return False, None
                    
        except SQLAlchemyError as e:
            logger.error(f"{self.name}: Database error: {e}")
            return False, None
        except Exception as e:
            logger.error(f"{self.name}: Unexpected error: {e}")
            return False, None
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash"""
        try:
            if self.password_type == 'bcrypt':
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            
            elif self.password_type == 'sha256':
                hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
                return hashed == stored_hash
            
            elif self.password_type == 'sha1':
                hashed = hashlib.sha1(password.encode('utf-8')).hexdigest()
                return hashed == stored_hash
            
            elif self.password_type == 'md5':
                hashed = hashlib.md5(password.encode('utf-8')).hexdigest()
                return hashed == stored_hash
            
            elif self.password_type == 'plain':
                return password == stored_hash
            
            else:
                logger.error(f"Unsupported password type: {self.password_type}")
                return False
                
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def _get_user_attributes_from_db(self, conn, username: str) -> Dict:
        """
        Get user attributes from attributes table.
        
        Assumes table structure:
        - username column
        - attribute column (RADIUS attribute name)
        - value column
        """
        try:
            query = text(f"""
                SELECT attribute, value
                FROM {self.attributes_table}
                WHERE username = :username
            """)
            
            results = conn.execute(query, {"username": username}).fetchall()
            
            radius_attrs = {}
            for row in results:
                attr_name, attr_value = row
                radius_attrs[attr_name] = attr_value
            
            logger.debug(f"Found {len(radius_attrs)} attributes for {username}")
            return radius_attrs
            
        except Exception as e:
            logger.error(f"Error fetching attributes for {username}: {e}")
            return {}
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test database connection"""
        if not self.database or not self.db_username:
            return False, "Database configuration incomplete"
        
        try:
            with self.engine.connect() as conn:
                # Test query
                result = conn.execute(text("SELECT 1")).fetchone()
                if result:
                    return True, f"Successfully connected to {self.db_type} database '{self.database}'"
                else:
                    return False, "Connection test query failed"
                    
        except SQLAlchemyError as e:
            return False, f"Database connection failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def get_user_attributes(self, username: str) -> Dict:
        """Get user attributes for RADIUS response"""
        if not self.attributes_table:
            return {}
        
        try:
            with self.engine.connect() as conn:
                return self._get_user_attributes_from_db(conn, username)
        except Exception as e:
            logger.error(f"Error getting attributes: {e}")
            return {}
    
    def __del__(self):
        """Cleanup: dispose of connection pool"""
        if hasattr(self, 'engine'):
            self.engine.dispose()
