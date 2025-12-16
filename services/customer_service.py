"""
Customer Management Service

Handles customer CRUD operations, account relationships, and OAuth token lifecycle.
"""
from datetime import datetime
from typing import List, Optional

from utils.logger import get_logger
from models.database import Customer, EmailAccount
from repositories.database_repository_interface import DatabaseRepositoryInterface
from services.oauth_token_service import OAuthTokenService

logger = get_logger(__name__)


class CustomerService:
    """
    Service for managing customers and their email accounts.

    Responsibilities:
    - Create/update customers from OAuth data
    - Manage customer-account relationships
    - Delete customers and cascade delete accounts
    - Revoke OAuth tokens on deletion
    """

    def __init__(self, repository: DatabaseRepositoryInterface):
        """
        Initialize customer service.

        Args:
            repository: Database repository for customer operations
        """
        self.repository = repository
        self.token_service = OAuthTokenService(repository)

    def get_or_create_customer(
        self,
        google_user_id: str,
        email_address: str,
        display_name: Optional[str] = None
    ) -> Customer:
        """
        Get existing customer by Google user ID or create new one.

        This is called during OAuth callback after user authorizes the app.

        Args:
            google_user_id: Google user ID from OAuth id_token (sub claim)
            email_address: Customer email address from Google profile
            display_name: Customer full name from Google profile

        Returns:
            Customer: Existing or newly created customer
        """
        # Try to find existing customer by Google user ID
        session = self.repository.get_session()
        try:
            customer = session.query(Customer).filter(
                Customer.google_user_id == google_user_id
            ).first()

            if customer:
                # Update last login time
                customer.last_login_at = datetime.utcnow()

                # Update email if changed
                if customer.email_address != email_address:
                    logger.info(
                        f"Customer {customer.id} email changed from "
                        f"{customer.email_address} to {email_address}"
                    )
                    customer.email_address = email_address

                # Update display name if provided and different
                if display_name and customer.display_name != display_name:
                    customer.display_name = display_name

                session.commit()
                session.refresh(customer)
                logger.info(f"Updated existing customer {customer.id} ({customer.email_address})")
                return customer

            # Create new customer
            new_customer = Customer(
                google_user_id=google_user_id,
                email_address=email_address,
                display_name=display_name,
                is_active=True,
                last_login_at=datetime.utcnow()
            )

            session.add(new_customer)
            session.commit()
            session.refresh(new_customer)

            logger.info(
                f"Created new customer {new_customer.id} ({new_customer.email_address})"
            )
            return new_customer

        except Exception as e:
            session.rollback()
            logger.exception(f"Failed to get or create customer for {email_address}")
            raise
        finally:
            session.close()

    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """
        Get customer by ID.

        Args:
            customer_id: Customer ID

        Returns:
            Customer or None if not found
        """
        return self.repository.get_by_id(Customer, customer_id)

    def get_customer_by_google_user_id(self, google_user_id: str) -> Optional[Customer]:
        """
        Get customer by Google user ID.

        Args:
            google_user_id: Google user ID (sub claim from OAuth)

        Returns:
            Customer or None if not found
        """
        session = self.repository.get_session()
        try:
            customer = session.query(Customer).filter(
                Customer.google_user_id == google_user_id
            ).first()
            return customer
        finally:
            session.close()

    def get_all_customers(self, active_only: bool = False) -> List[Customer]:
        """
        Get all customers.

        Args:
            active_only: If True, only return active customers

        Returns:
            List of customers
        """
        session = self.repository.get_session()
        try:
            query = session.query(Customer)

            if active_only:
                query = query.filter(Customer.is_active.is_(True))

            customers = query.order_by(Customer.created_at.desc()).all()
            return customers
        finally:
            session.close()

    def get_customer_accounts(self, customer_id: int) -> List[EmailAccount]:
        """
        Get all email accounts for a customer.

        Args:
            customer_id: Customer ID

        Returns:
            List of email accounts
        """
        session = self.repository.get_session()
        try:
            accounts = session.query(EmailAccount).filter(
                EmailAccount.customer_id == customer_id
            ).order_by(EmailAccount.created_at.desc()).all()
            return accounts
        finally:
            session.close()

    def get_customer_account_count(self, customer_id: int) -> int:
        """
        Get count of email accounts for a customer.

        Args:
            customer_id: Customer ID

        Returns:
            Number of accounts
        """
        session = self.repository.get_session()
        try:
            count = session.query(EmailAccount).filter(
                EmailAccount.customer_id == customer_id
            ).count()
            return count
        finally:
            session.close()

    def delete_customer(self, customer_id: int) -> dict:
        """
        Delete customer and all associated accounts.

        This will:
        1. Revoke all OAuth tokens for customer's accounts
        2. Cascade delete all accounts (via FK constraint)
        3. Delete customer record

        Args:
            customer_id: Customer ID to delete

        Returns:
            dict: Deletion summary with counts

        Raises:
            ValueError: If customer not found
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        # Get all accounts before deletion
        accounts = self.get_customer_accounts(customer_id)
        account_count = len(accounts)
        tokens_revoked = 0

        # Revoke OAuth tokens for all accounts
        for account in accounts:
            if account.oauth_refresh_token:
                try:
                    if self.token_service.revoke_token(account.oauth_refresh_token):
                        tokens_revoked += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to revoke token for account {account.email_address}: {e}"
                    )

        # Delete customer (accounts will be cascade deleted)
        session = self.repository.get_session()
        try:
            session.delete(customer)
            session.commit()

            logger.info(
                f"Deleted customer {customer_id} ({customer.email_address}). "
                f"Accounts deleted: {account_count}, Tokens revoked: {tokens_revoked}"
            )

            return {
                "customer_id": customer_id,
                "customer_email": customer.email_address,
                "accounts_deleted": account_count,
                "tokens_revoked": tokens_revoked
            }

        except Exception as e:
            session.rollback()
            logger.exception(f"Failed to delete customer {customer_id}")
            raise
        finally:
            session.close()

    def deactivate_customer(self, customer_id: int) -> Customer:
        """
        Deactivate a customer (soft delete).

        Args:
            customer_id: Customer ID

        Returns:
            Updated customer

        Raises:
            ValueError: If customer not found
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        session = self.repository.get_session()
        try:
            customer.is_active = False
            session.commit()
            session.refresh(customer)

            logger.info(f"Deactivated customer {customer_id} ({customer.email_address})")
            return customer

        except Exception as e:
            session.rollback()
            logger.exception(f"Failed to deactivate customer {customer_id}")
            raise
        finally:
            session.close()

    def reactivate_customer(self, customer_id: int) -> Customer:
        """
        Reactivate a deactivated customer.

        Args:
            customer_id: Customer ID

        Returns:
            Updated customer

        Raises:
            ValueError: If customer not found
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        session = self.repository.get_session()
        try:
            customer.is_active = True
            session.commit()
            session.refresh(customer)

            logger.info(f"Reactivated customer {customer_id} ({customer.email_address})")
            return customer

        except Exception as e:
            session.rollback()
            logger.exception(f"Failed to reactivate customer {customer_id}")
            raise
        finally:
            session.close()
