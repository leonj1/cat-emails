"""
Settings service for managing user preferences and configuration
"""
import logging
from typing import Optional, Any, Union
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime

from models.database import UserSettings, init_database

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing user settings and preferences"""
    
    def __init__(self, db_path: str = "./email_summaries/summaries.db"):
        self.db_path = db_path
        self.engine = init_database(db_path)
        self.Session = sessionmaker(bind=self.engine)
        self._initialize_default_settings()
    
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
        with self.Session() as session:
            setting = session.query(UserSettings).filter_by(setting_key=key).first()
            
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
            with self.Session() as session:
                setting = session.query(UserSettings).filter_by(setting_key=key).first()
                
                if setting:
                    # Update existing setting
                    setting.setting_value = str(value)
                    setting.setting_type = setting_type
                    if description:
                        setting.description = description
                    setting.updated_at = datetime.utcnow()
                else:
                    # Create new setting
                    setting = UserSettings(
                        setting_key=key,
                        setting_value=str(value),
                        setting_type=setting_type,
                        description=description
                    )
                    session.add(setting)
                
                session.commit()
                logger.info(f"Updated setting: {key} = {value}")
                return True
                
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False
    
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
