"""
Database repository pattern implementation.

This package provides abstraction for database access, making it easy to:
- Swap database providers (e.g., local SQLite, MySQL, SQLite Cloud)
- Write unit tests with mock repositories
- Maintain consistent data access patterns
"""

from repositories.database_repository_interface import DatabaseRepositoryInterface
from repositories.sqlalchemy_repository import SQLAlchemyRepository
from repositories.mysql_repository import MySQLRepository

__all__ = [
    'DatabaseRepositoryInterface',
    'SQLAlchemyRepository',
    'MySQLRepository',
]
