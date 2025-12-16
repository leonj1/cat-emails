"""
Customer Management Endpoints

Provides CRUD operations for customers and their email accounts.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header, status, Path

from utils.logger import get_logger
from services.customer_service import CustomerService
from models.customer_models import (
    CustomerInfo,
    CustomerListResponse,
    CustomerAccountsResponse,
    CustomerDeleteResponse
)
from models.account_models import EmailAccountInfo
from utils.password_utils import mask_password
from repositories.database_repository_interface import DatabaseRepositoryInterface

logger = get_logger(__name__)

# Create router for customer endpoints
router = APIRouter(prefix="/api/customers", tags=["Customers"])


def verify_api_key_dependency(x_api_key: Optional[str] = Header(None)) -> bool:
    """Dependency for API key verification"""
    import os
    api_key = os.getenv("API_KEY")
    if api_key and (not x_api_key or x_api_key != api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return True


def create_customer_endpoints(repository: DatabaseRepositoryInterface):
    """
    Factory function to create customer endpoints with injected dependencies.

    Args:
        repository: Database repository for customer operations

    Returns:
        APIRouter: Configured router with customer endpoints
    """

    @router.get(
        "",
        response_model=CustomerListResponse,
        summary="List All Customers",
        description="Get a list of all customers in the system"
    )
    async def get_all_customers(
        active_only: bool = False,
        x_api_key: Optional[str] = Header(None)
    ):
        """
        List all customers.

        Query Parameters:
            active_only: If true, only return active customers (default: false)

        Returns:
            CustomerListResponse: List of customers with account counts

        Raises:
            401: Invalid or missing API key
            500: Internal server error
        """
        verify_api_key_dependency(x_api_key)

        try:
            customer_service = CustomerService(repository)
            customers = customer_service.get_all_customers(active_only=active_only)

            # Build customer info list
            customer_infos: List[CustomerInfo] = []
            for customer in customers:
                account_count = customer_service.get_customer_account_count(customer.id)
                customer_infos.append(
                    CustomerInfo(
                        id=customer.id,
                        google_user_id=customer.google_user_id,
                        email_address=customer.email_address,
                        display_name=customer.display_name,
                        is_active=customer.is_active,
                        account_count=account_count,
                        created_at=customer.created_at,
                        last_login_at=customer.last_login_at
                    )
                )

            logger.info(f"Retrieved {len(customer_infos)} customers (active_only={active_only})")

            return CustomerListResponse(
                customers=customer_infos,
                total_count=len(customer_infos),
                timestamp=datetime.utcnow().isoformat()
            )

        except Exception as e:
            logger.exception("Error retrieving customers")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve customers"
            ) from e

    @router.get(
        "/{customer_id}",
        response_model=CustomerInfo,
        summary="Get Customer by ID",
        description="Get detailed information about a specific customer"
    )
    async def get_customer(
        customer_id: int = Path(..., description="Customer ID"),
        x_api_key: Optional[str] = Header(None)
    ):
        """
        Get customer by ID.

        Path Parameters:
            customer_id: Customer ID

        Returns:
            CustomerInfo: Customer information with account count

        Raises:
            401: Invalid or missing API key
            404: Customer not found
            500: Internal server error
        """
        verify_api_key_dependency(x_api_key)

        try:
            customer_service = CustomerService(repository)
            customer = customer_service.get_customer_by_id(customer_id)

            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer {customer_id} not found"
                )

            account_count = customer_service.get_customer_account_count(customer.id)

            return CustomerInfo(
                id=customer.id,
                google_user_id=customer.google_user_id,
                email_address=customer.email_address,
                display_name=customer.display_name,
                is_active=customer.is_active,
                account_count=account_count,
                created_at=customer.created_at,
                last_login_at=customer.last_login_at
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error retrieving customer {customer_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve customer"
            ) from e

    @router.get(
        "/{customer_id}/accounts",
        response_model=CustomerAccountsResponse,
        summary="Get Customer's Email Accounts",
        description="Get all email accounts for a specific customer"
    )
    async def get_customer_accounts(
        customer_id: int = Path(..., description="Customer ID"),
        x_api_key: Optional[str] = Header(None)
    ):
        """
        Get all email accounts for a customer.

        Path Parameters:
            customer_id: Customer ID

        Returns:
            CustomerAccountsResponse: Customer info with list of accounts

        Raises:
            401: Invalid or missing API key
            404: Customer not found
            500: Internal server error
        """
        verify_api_key_dependency(x_api_key)

        try:
            customer_service = CustomerService(repository)
            customer = customer_service.get_customer_by_id(customer_id)

            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer {customer_id} not found"
                )

            accounts = customer_service.get_customer_accounts(customer_id)

            # Build account info list
            account_infos: List[EmailAccountInfo] = []
            for account in accounts:
                account_infos.append(
                    EmailAccountInfo(
                        id=account.id,
                        email_address=account.email_address,
                        display_name=account.display_name,
                        masked_password=mask_password(account.app_password) if account.app_password else "OAuth",
                        password_length=len(account.app_password) if account.app_password else 0,
                        is_active=account.is_active,
                        last_scan_at=account.last_scan_at,
                        created_at=account.created_at
                    )
                )

            customer_info = CustomerInfo(
                id=customer.id,
                google_user_id=customer.google_user_id,
                email_address=customer.email_address,
                display_name=customer.display_name,
                is_active=customer.is_active,
                account_count=len(account_infos),
                created_at=customer.created_at,
                last_login_at=customer.last_login_at
            )

            logger.info(f"Retrieved {len(account_infos)} accounts for customer {customer_id}")

            return CustomerAccountsResponse(
                customer=customer_info,
                accounts=account_infos,
                total_count=len(account_infos),
                timestamp=datetime.utcnow().isoformat()
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error retrieving accounts for customer {customer_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve customer accounts"
            ) from e

    @router.delete(
        "/{customer_id}",
        response_model=CustomerDeleteResponse,
        summary="Delete Customer",
        description="Delete customer and all associated accounts (revokes OAuth tokens)"
    )
    async def delete_customer(
        customer_id: int = Path(..., description="Customer ID"),
        x_api_key: Optional[str] = Header(None)
    ):
        """
        Delete a customer and all associated accounts.

        This operation:
        1. Revokes all OAuth tokens for customer's accounts
        2. Cascade deletes all email accounts
        3. Deletes customer record

        Path Parameters:
            customer_id: Customer ID to delete

        Returns:
            CustomerDeleteResponse: Deletion summary with counts

        Raises:
            401: Invalid or missing API key
            404: Customer not found
            500: Internal server error
        """
        verify_api_key_dependency(x_api_key)

        try:
            customer_service = CustomerService(repository)
            result = customer_service.delete_customer(customer_id)

            logger.info(
                f"Deleted customer {customer_id}: "
                f"{result['accounts_deleted']} accounts, "
                f"{result['tokens_revoked']} tokens revoked"
            )

            return CustomerDeleteResponse(
                status="success",
                message=f"Customer {result['customer_email']} deleted successfully",
                customer_id=result['customer_id'],
                accounts_deleted=result['accounts_deleted'],
                tokens_revoked=result['tokens_revoked'],
                timestamp=datetime.utcnow().isoformat()
            )

        except ValueError as e:
            # Customer not found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.exception(f"Error deleting customer {customer_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete customer"
            ) from e

    return router
