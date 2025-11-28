"""
Tally Cleanup Service.

This service handles cleanup of old category tallies based on the
configured retention period.
"""
from datetime import date, timedelta
from typing import Optional

from repositories.category_tally_repository_interface import ICategoryTallyRepository
from services.interfaces.category_aggregation_config_interface import (
    ICategoryAggregationConfig
)
from utils.logger import get_logger

logger = get_logger(__name__)


class TallyCleanupService:
    """
    Service for cleaning up old category tally data.

    This service removes tallies older than the configured retention period
    to prevent unbounded database growth.
    """

    def __init__(
        self,
        repository: ICategoryTallyRepository,
        config: ICategoryAggregationConfig
    ):
        """
        Initialize the cleanup service.

        Args:
            repository: Repository for accessing tally data
            config: Configuration for retention settings
        """
        self._repository = repository
        self._config = config

    def cleanup_old_tallies(
        self,
        email_address: str,
        reference_date: Optional[date]
    ) -> int:
        """
        Remove tallies older than the retention period for an account.

        Args:
            email_address: Email account to clean up
            reference_date: Reference date for cleanup (None = use today)

        Returns:
            Number of tallies deleted
        """
        if reference_date is None:
            reference_date = date.today()

        retention_days = self._config.get_retention_days()
        cutoff_date = reference_date - timedelta(days=retention_days)

        logger.info(
            f"Cleaning up tallies for {email_address} "
            f"older than {cutoff_date.isoformat()}"
        )

        deleted_count = self._repository.delete_tallies_before(
            email_address,
            cutoff_date
        )

        logger.info(
            f"Cleaned up {deleted_count} tallies for {email_address}"
        )

        return deleted_count
