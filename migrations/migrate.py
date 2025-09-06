#!/usr/bin/env python3
"""
Migration Runner for Cat-Emails Database

This script provides a centralized way to run database migrations,
track migration history, and manage schema versions.

Usage:
    python migrations/migrate.py --action upgrade
    python migrations/migrate.py --action downgrade --target 000
    python migrations/migrate.py --status
"""

import logging
import sys
import importlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import create_engine, Column, Integer, String, DateTime, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import models
sys.path.append(str(Path(__file__).parent.parent))
from models.database import get_database_url

Base = declarative_base()


class MigrationHistory(Base):
    """Track applied migrations"""
    __tablename__ = 'migration_history'
    
    id = Column(Integer, primary_key=True)
    version = Column(String(10), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    duration_seconds = Column(Integer, nullable=True)


class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "./email_summaries/summaries.db"
        self.engine = create_engine(get_database_url(self.db_path))
        self.Session = sessionmaker(bind=self.engine)
        self.migrations_dir = Path(__file__).parent
        
        # Ensure migration history table exists
        self._init_migration_history()
    
    def _init_migration_history(self):
        """Create migration history table if it doesn't exist"""
        inspector = inspect(self.engine)
        if 'migration_history' not in inspector.get_table_names():
            MigrationHistory.__table__.create(self.engine)
            logger.info("Created migration_history table")
    
    def _get_available_migrations(self) -> List[Tuple[str, str, Path]]:
        """Get list of available migration files"""
        migrations = []
        pattern = re.compile(r'^(\d{3})_(.+)\.py$')
        
        for file_path in self.migrations_dir.glob('*.py'):
            if file_path.name.startswith('__') or file_path.name == 'migrate.py':
                continue
                
            match = pattern.match(file_path.name)
            if match:
                version, name = match.groups()
                migrations.append((version, name, file_path))
        
        # Sort by version number
        migrations.sort(key=lambda x: x[0])
        return migrations
    
    def _get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations from database"""
        session = self.Session()
        try:
            applied = session.query(MigrationHistory.version).order_by(MigrationHistory.version).all()
            return [version[0] for version in applied]
        finally:
            session.close()
    
    def _import_migration(self, version: str, file_path: Path):
        """Import a migration module"""
        module_name = f"migrations.{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    def _record_migration(self, version: str, name: str, duration: Optional[float] = None):
        """Record successful migration in history"""
        session = self.Session()
        try:
            migration_record = MigrationHistory(
                version=version,
                name=name,
                duration_seconds=int(duration) if duration else None
            )
            session.add(migration_record)
            session.commit()
            logger.info(f"Recorded migration {version} in history")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record migration: {e}")
            raise
        finally:
            session.close()
    
    def _remove_migration_record(self, version: str):
        """Remove migration record from history"""
        session = self.Session()
        try:
            migration_record = session.query(MigrationHistory).filter_by(version=version).first()
            if migration_record:
                session.delete(migration_record)
                session.commit()
                logger.info(f"Removed migration {version} from history")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to remove migration record: {e}")
            raise
        finally:
            session.close()
    
    def status(self):
        """Show migration status"""
        available_migrations = self._get_available_migrations()
        applied_migrations = set(self._get_applied_migrations())
        
        print("Migration Status:")
        print("=" * 50)
        print(f"Database: {self.db_path}")
        print(f"Total migrations available: {len(available_migrations)}")
        print(f"Applied migrations: {len(applied_migrations)}")
        print()
        
        if not available_migrations:
            print("No migrations found.")
            return
        
        print("Migrations:")
        for version, name, file_path in available_migrations:
            status = "✓ Applied" if version in applied_migrations else "○ Pending"
            print(f"  {version}: {name.replace('_', ' ').title()} [{status}]")
    
    def upgrade(self, target: Optional[str] = None):
        """Apply pending migrations up to target version"""
        available_migrations = self._get_available_migrations()
        applied_migrations = set(self._get_applied_migrations())
        
        # Determine which migrations to run
        migrations_to_run = []
        for version, name, file_path in available_migrations:
            if version in applied_migrations:
                continue  # Skip already applied migrations
            
            if target and version > target:
                break  # Stop if we've reached the target version
            
            migrations_to_run.append((version, name, file_path))
        
        if not migrations_to_run:
            logger.info("No pending migrations to apply")
            return
        
        logger.info(f"Applying {len(migrations_to_run)} migration(s)")
        
        for version, name, file_path in migrations_to_run:
            logger.info(f"Applying migration {version}: {name}")
            start_time = datetime.now()
            
            try:
                # Import and run the migration
                migration_module = self._import_migration(version, file_path)
                migration_module.upgrade(self.db_path)
                
                # Record successful migration
                duration = (datetime.now() - start_time).total_seconds()
                self._record_migration(version, name, duration)
                
                logger.info(f"✓ Migration {version} completed successfully")
                
            except Exception as e:
                logger.error(f"✗ Migration {version} failed: {e}")
                raise
        
        logger.info("All migrations applied successfully")
    
    def downgrade(self, target: Optional[str] = None):
        """Rollback migrations down to target version"""
        available_migrations = self._get_available_migrations()
        applied_migrations = self._get_applied_migrations()
        
        # Create lookup for migration info
        migration_lookup = {version: (name, file_path) for version, name, file_path in available_migrations}
        
        # Determine which migrations to rollback (in reverse order)
        migrations_to_rollback = []
        for version in reversed(applied_migrations):
            if target and version <= target:
                break  # Stop if we've reached the target version
            
            if version in migration_lookup:
                name, file_path = migration_lookup[version]
                migrations_to_rollback.append((version, name, file_path))
        
        if not migrations_to_rollback:
            logger.info("No migrations to rollback")
            return
        
        logger.info(f"Rolling back {len(migrations_to_rollback)} migration(s)")
        
        for version, name, file_path in migrations_to_rollback:
            logger.info(f"Rolling back migration {version}: {name}")
            
            try:
                # Import and run the rollback
                migration_module = self._import_migration(version, file_path)
                migration_module.downgrade(self.db_path)
                
                # Remove from migration history
                self._remove_migration_record(version)
                
                logger.info(f"✓ Migration {version} rolled back successfully")
                
            except Exception as e:
                logger.error(f"✗ Rollback of migration {version} failed: {e}")
                raise
        
        logger.info("All migrations rolled back successfully")


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration Manager")
    parser.add_argument('--action', choices=['upgrade', 'downgrade', 'status'], 
                       default='status', help='Migration action to perform')
    parser.add_argument('--target', type=str, 
                       help='Target migration version (for upgrade/downgrade)')
    parser.add_argument('--db-path', type=str,
                       help='Database path (default: ./email_summaries/summaries.db)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        manager = MigrationManager(args.db_path)
        
        if args.action == 'status':
            manager.status()
        elif args.action == 'upgrade':
            manager.upgrade(args.target)
        elif args.action == 'downgrade':
            manager.downgrade(args.target)
            
    except Exception as e:
        logger.error(f"Migration operation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # Add the missing import for importlib.util
    import importlib.util
    main()