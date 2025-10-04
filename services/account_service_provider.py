import logging
from fastapi import HTTPException, status
from services.account_service_provider_interface import AccountServiceProviderInterface
from services.account_category_service import AccountCategoryService

logger = logging.getLogger(__name__)


class AccountServiceProvider(AccountServiceProviderInterface):
    """Default implementation of AccountServiceProviderInterface."""

    def get_service(self) -> AccountCategoryService:
        """
        Get an AccountCategoryService instance.

        Returns:
            AccountCategoryService: An initialized service instance

        Raises:
            HTTPException: If service cannot be created (500 Internal Server Error)
        """
        try:
            return AccountCategoryService()
        except Exception as e:
            logger.error(f"Failed to create AccountCategoryService: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database service unavailable"
            )
