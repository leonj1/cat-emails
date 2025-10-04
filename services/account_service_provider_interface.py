from abc import ABC, abstractmethod
from services.account_category_service import AccountCategoryService


class AccountServiceProviderInterface(ABC):
    """Interface for providing AccountCategoryService instances."""

    @abstractmethod
    def get_service(self) -> AccountCategoryService:
        """
        Get an AccountCategoryService instance.

        Returns:
            AccountCategoryService: An initialized service instance

        Raises:
            Exception: If service cannot be created
        """
        pass
