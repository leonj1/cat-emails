"""
Settings service for managing user preferences and configuration
"""
import logging
from utils.logger import get_logger
import os
from typing import Optional, Any, Union
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime

from models.database import UserSettings, init_database
from repositories.database_repository_interface import DatabaseRepositoryInterface
from repositories.mysql_repository import MySQLRepository
from repositories.sqlalchemy_repository import SQLAlchemyRepository

logger = get_logger(__name__)


class SettingsService:
    """Service for managing user settings and preferences"""
    
    def __init__(self, repository: Optional[DatabaseRepositoryInterface] = None, db_path: Optional[str] = None):
        """
        Initialize settings service with dependency injection.

        Args:
            repository: Optional repository implementation. If not provided, auto-detects
                       MySQL (if credentials available) or falls back to SQLite
            db_path: Optional database path (used for SQLite fallback)

        Raises:
            ValueError: If no repository can be initialized (no MySQL credentials and no SQLite path)
        """
        if repository:
            self.repository = repository
            # Ensure repository is connected
            if not self.repository.is_connected():
                if not db_path:
                    db_path = os.getenv("DATABASE_PATH")
                if not db_path:
                    raise ValueError(
                        "SettingsService requires a connected repository. "
                        "Provide a connected repository or specify db_path/DATABASE_PATH."
                    )
                self.repository.connect(db_path)
        else:
            # Auto-detect repository type based on available configuration
            self.repository = self._create_default_repository(db_path)

        # Maintain backward compatibility
        self.db_path = getattr(self.repository, 'db_path', None)
        self.engine = getattr(self.repository, 'engine', None)
        self.Session = getattr(self.repository, 'SessionFactory', None)

        # Validate that SessionFactory is available
        if self.Session is None:
            raise ValueError(
                "SettingsService requires a connected repository with an available SessionFactory. "
                "Repository connection may have failed."
            )

        self._initialize_default_settings()

    def _create_default_repository(self, db_path: Optional[str] = None) -> DatabaseRepositoryInterface:
        """
        Create a default repository based on available configuration.
        Tries MySQL first, falls back to SQLite if MySQL credentials not available.

        Args:
            db_path: Optional database path for SQLite fallback

        Returns:
            DatabaseRepositoryInterface: Connected repository instance

        Raises:
            ValueError: If neither MySQL nor SQLite can be configured
        """
        # Try MySQL first
        try:
            mysql_repo = MySQLRepository()
            if mysql_repo.is_connected():
                logger.info("SettingsService using MySQL repository")
                return mysql_repo
        except (ValueError, OSError, ConnectionError) as e:
            logger.debug(f"MySQL not available, trying SQLite: {e}")

        # Fall back to SQLite
        if not db_path:
            db_path = os.getenv("DATABASE_PATH")

        if db_path:
            try:
                sqlite_repo = SQLAlchemyRepository(db_path)
                logger.info("SettingsService using SQLite repository")
                return sqlite_repo
            except (ValueError, OSError, ConnectionError) as e:
                logger.exception("Failed to initialize SQLite repository")
                raise ValueError(
                    "SettingsService could not initialize any repository. "
                    "Set MySQL credentials (MYSQL_HOST, MYSQL_DATABASE, MYSQL_USER) "
                    "or DATABASE_PATH for SQLite."
                ) from e
        else:
            raise ValueError(
                "SettingsService requires database configuration. "
                "Either provide MySQL credentials (MYSQL_HOST, MYSQL_DATABASE, MYSQL_USER) "
                "or set DATABASE_PATH for SQLite."
            )
    
    def _initialize_default_settings(self):
        """Initialize default settings if they don't exist"""
        defaults = [
            {
                'setting_key': 'lookback_hours',
                'setting_value': '2',
                'setting_type': 'integer',
                'description': 'Number of hours to look back when scanning for emails'
            },
            {
                'setting_key': 'scan_interval_minutes',
                'setting_value': '5',
                'setting_type': 'integer',
                'description': 'Interval in minutes between background email scans'
            }
        ]
        
        with self.Session() as session:
            for default in defaults:
                existing = session.query(UserSettings).filter_by(
                    setting_key=default['setting_key']
                ).first()
                
                if not existing:
                    setting = UserSettings(**default)
                    session.add(setting)
                    logger.info(f"Initialized default setting: {default['setting_key']} = {default['setting_value']}")
            
            session.commit()
    
    def get_setting(self, key: str, default_value: Any = None) -> Any:
        """Get a setting value by key, with type conversion"""
        setting = self.repository.get_setting(key)
        
        if not setting:
            return default_value
        
        # Convert based on setting type
        if setting.setting_type == 'integer':
            return int(setting.setting_value)
        elif setting.setting_type == 'float':
            return float(setting.setting_value)
        elif setting.setting_type == 'boolean':
            return setting.setting_value.lower() in ('true', '1', 'yes')
        else:
            return setting.setting_value
    
    def set_setting(self, key: str, value: Any, setting_type: str = 'string', description: str = '') -> bool:
        """Set a setting value with automatic type conversion"""
        try:
            self.repository.set_setting(key, str(value), setting_type, description)
            logger.info(f"Updated setting: {key} = {value}")
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False
        else:
            return True
    
    def get_lookback_hours(self) -> int:
        """Get the email lookback hours setting"""
        return self.get_setting('lookback_hours', 2)
    
    def set_lookback_hours(self, hours: int) -> bool:
        """Set the email lookback hours setting"""
        return self.set_setting(
            'lookback_hours', 
            hours, 
            'integer',
            'Number of hours to look back when scanning for emails'
        )
    
    def get_all_settings(self) -> dict:
        """Get all settings as a dictionary"""
        with self.Session() as session:
            settings = session.query(UserSettings).all()
            
            result = {}
            for setting in settings:
                # Convert based on type
                if setting.setting_type == 'integer':
                    value = int(setting.setting_value)
                elif setting.setting_type == 'float':
                    value = float(setting.setting_value)
                elif setting.setting_type == 'boolean':
                    value = setting.setting_value.lower() in ('true', '1', 'yes')
                else:
                    value = setting.setting_value
                
                result[setting.setting_key] = {
                    'value': value,
                    'type': setting.setting_type,
                    'description': setting.description,
                    'updated_at': setting.updated_at
                }
            
            return result
