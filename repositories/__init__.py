"""
Database repository pattern implementation.

This package provides abstraction for database access, making it easy to:
- Swap database providers (e.g., local SQLite to SQLite Cloud)
- Write unit tests with mock repositories
- Maintain consistent data access patterns
"""

from repositories.database_repository_interface import DatabaseRepositoryInterface
from repositories.sqlalchemy_repository import SQLAlchemyRepository

__all__ = [
    'DatabaseRepositoryInterface',
    'SQLAlchemyRepository',
]
