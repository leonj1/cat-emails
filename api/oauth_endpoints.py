"""
OAuth 2.0 Authorization Flow Endpoints

Provides OAuth authorization and callback endpoints for Gmail account authentication.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Header, status
from fastapi.responses import RedirectResponse

from utils.logger import get_logger
from services.oauth_state_service import OAuthStateService
from services.oauth_helpers import (
    build_google_oauth_url,
    exchange_authorization_code_for_tokens,
    decode_and_verify_id_token,
)
from services.customer_service import CustomerService
from models.oauth_models import OAuthCallbackResponse
from models.database import EmailAccount
from repositories.database_repository_interface import DatabaseRepositoryInterface

logger = get_logger(__name__)

# Create router for OAuth endpoints
router = APIRouter(prefix="/api/oauth", tags=["OAuth"])


def create_oauth_endpoints(repository: DatabaseRepositoryInterface):
    """
    Factory function to create OAuth endpoints with injected dependencies.

    Args:
        repository: Database repository for customer/account operations

    Returns:
        APIRouter: Configured router with OAuth endpoints
    """

    @router.get(
        "/authorize",
        summary="Initiate OAuth 2.0 Authorization",
        description="Redirects user to Google OAuth consent screen to authorize Gmail access"
    )
    async def oauth_authorize(
        customer_email: Optional[str] = Query(None, description="Email hint for Google login"),
        account_email: Optional[str] = Query(None, description="Specific Gmail account to add"),
        x_api_key: Optional[str] = Header(None)
    ):
        """
        Initiate OAuth 2.0 authorization flow.

        This endpoint redirects the user to Google's OAuth consent screen where they
        can authorize the application to access their Gmail account.

        Query Parameters:
            customer_email: Optional email hint to pre-fill Google login screen
            account_email: Optional specific Gmail account to link after authorization

        Returns:
            302 Redirect: Redirects to Google OAuth consent screen

        Raises:
            500: OAuth configuration error
        """
        # Note: No API key validation - this is the entry point for user authorization

        try:
            # Generate secure state parameter for CSRF protection
            state_service = OAuthStateService()
            state = state_service.generate_state(
                customer_email=customer_email,
                account_email=account_email
            )

            # Get OAuth configuration from environment
            import os
            redirect_uri = os.getenv("OAUTH_REDIRECT_URI")
            if not redirect_uri:
                raise ValueError("OAUTH_REDIRECT_URI not configured in environment")

            # Build Google OAuth URL
            oauth_url = build_google_oauth_url(
                state=state,
                redirect_uri=redirect_uri,
                login_hint=customer_email
            )

            logger.info(
                f"OAuth authorization initiated for customer_email={customer_email}, "
                f"account_email={account_email}"
            )

            return RedirectResponse(oauth_url)

        except Exception as e:
            logger.exception("Failed to initiate OAuth authorization")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OAuth configuration error: {str(e)}"
            ) from e

    @router.get(
        "/callback",
        response_model=OAuthCallbackResponse,
        summary="OAuth 2.0 Callback Handler",
        description="Handles OAuth callback from Google and creates/updates customer and account"
    )
    async def oauth_callback(
        code: str = Query(..., description="Authorization code from Google"),
        state: str = Query(..., description="State parameter for CSRF protection"),
        error: Optional[str] = Query(None, description="Error code if authorization failed"),
        error_description: Optional[str] = Query(None, description="Human-readable error")
    ):
        """
        Handle OAuth 2.0 callback from Google.

        This endpoint:
        1. Validates the state parameter (CSRF protection)
        2. Exchanges authorization code for OAuth tokens
        3. Decodes ID token to get user identity
        4. Creates or updates customer record
        5. Creates or updates email account with OAuth tokens

        Query Parameters:
            code: Authorization code from Google (required)
            state: State parameter for validation (required)
            error: Error code if authorization failed
            error_description: Human-readable error message

        Returns:
            OAuthCallbackResponse: Success response with customer and account details

        Raises:
            400: Invalid state, expired state, or OAuth error
            500: Internal server error
        """
        # Handle OAuth errors from Google
        if error:
            logger.warning(f"OAuth authorization failed: {error} - {error_description}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth authorization failed: {error} - {error_description}"
            )

        try:
            # Step 1: Validate state parameter (CSRF protection)
            state_service = OAuthStateService()
            state_data = state_service.validate_and_decode_state(state)
            logger.info(f"State validated successfully (nonce: {state_data['nonce'][:8]}...)")

            # Step 2: Exchange authorization code for tokens
            import os
            redirect_uri = os.getenv("OAUTH_REDIRECT_URI")
            token_response = exchange_authorization_code_for_tokens(
                authorization_code=code,
                redirect_uri=redirect_uri
            )

            # Verify we got a refresh token
            if "refresh_token" not in token_response:
                logger.error(
                    "No refresh_token in OAuth response. User may have already authorized. "
                    "prompt=consent should force refresh_token."
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OAuth authorization did not return a refresh token. "
                           "Please revoke access at https://myaccount.google.com/permissions "
                           "and try again."
                )

            # Step 3: Decode and verify ID token to get user identity
            id_token = token_response.get("id_token")
            if not id_token:
                raise ValueError("No id_token in OAuth response")

            user_info = decode_and_verify_id_token(id_token)

            # Extract user identity
            google_user_id = user_info.get("sub")
            user_email = user_info.get("email")
            user_name = user_info.get("name")

            if not google_user_id or not user_email:
                raise ValueError("ID token missing required fields (sub, email)")

            logger.info(f"User authenticated: {user_email} (Google ID: {google_user_id[:10]}...)")

            # Step 4: Create or update customer
            customer_service = CustomerService(repository)
            customer = customer_service.get_or_create_customer(
                google_user_id=google_user_id,
                email_address=user_email,
                display_name=user_name
            )

            # Step 5: Create or update email account with OAuth tokens
            account_email = state_data.get("account_email") or user_email

            # Get or create account
            session = repository.get_session()
            try:
                account = session.query(EmailAccount).filter(
                    EmailAccount.email_address == account_email
                ).first()

                if account:
                    # Update existing account with OAuth tokens
                    account.customer_id = customer.id
                    account.auth_method = "oauth"
                    account.oauth_refresh_token = token_response["refresh_token"]
                    account.oauth_access_token = token_response["access_token"]
                    account.oauth_token_expires_at = datetime.utcnow() + \
                        timedelta(seconds=token_response.get("expires_in", 3600))
                    account.oauth_scope = token_response.get("scope")
                    account.oauth_token_type = token_response.get("token_type", "Bearer")
                    account.oauth_authorized_at = datetime.utcnow()
                    account.is_active = True

                    logger.info(f"Updated existing account {account_email} with OAuth tokens")
                else:
                    # Create new account
                    from datetime import timedelta
                    account = EmailAccount(
                        email_address=account_email,
                        customer_id=customer.id,
                        auth_method="oauth",
                        oauth_refresh_token=token_response["refresh_token"],
                        oauth_access_token=token_response["access_token"],
                        oauth_token_expires_at=datetime.utcnow() + \
                            timedelta(seconds=token_response.get("expires_in", 3600)),
                        oauth_scope=token_response.get("scope"),
                        oauth_token_type=token_response.get("token_type", "Bearer"),
                        oauth_authorized_at=datetime.utcnow(),
                        is_active=True
                    )
                    session.add(account)
                    logger.info(f"Created new account {account_email} with OAuth tokens")

                session.commit()
                session.refresh(account)

            finally:
                session.close()

            # Return success response
            return OAuthCallbackResponse(
                status="success",
                message=f"Successfully authorized {account_email}",
                customer_id=customer.id,
                customer_email=customer.email_address,
                account_id=account.id,
                account_email=account.email_address,
                timestamp=datetime.utcnow().isoformat()
            )

        except ValueError as e:
            logger.warning(f"OAuth callback validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.exception("OAuth callback error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth callback processing failed"
            ) from e

    return router
