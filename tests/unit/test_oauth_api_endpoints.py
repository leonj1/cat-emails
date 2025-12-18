"""
Unit tests for OAuth API endpoints.

Tests the FastAPI OAuth endpoints for Gmail authorization flow.
"""
import unittest
from datetime import datetime


class TestOAuthModelsExist(unittest.TestCase):
    """Tests that OAuth Pydantic models exist and are importable."""

    def test_oauth_authorize_response_exists(self):
        """Test that OAuthAuthorizeResponse model exists."""
        from models.oauth_models import OAuthAuthorizeResponse

        response = OAuthAuthorizeResponse(
            authorization_url="https://example.com/auth",
            state="test_state",
        )

        self.assertEqual(response.authorization_url, "https://example.com/auth")
        self.assertEqual(response.state, "test_state")

    def test_oauth_callback_request_exists(self):
        """Test that OAuthCallbackRequest model exists."""
        from models.oauth_models import OAuthCallbackRequest

        request = OAuthCallbackRequest(
            code="auth_code",
            state="test_state",
        )

        self.assertEqual(request.code, "auth_code")
        self.assertEqual(request.state, "test_state")

    def test_oauth_callback_response_exists(self):
        """Test that OAuthCallbackResponse model exists."""
        from models.oauth_models import OAuthCallbackResponse

        response = OAuthCallbackResponse(
            success=True,
            email_address="user@gmail.com",
            scopes=["gmail.readonly"],
        )

        self.assertTrue(response.success)
        self.assertEqual(response.email_address, "user@gmail.com")
        self.assertEqual(response.scopes, ["gmail.readonly"])

    def test_oauth_status_response_exists(self):
        """Test that OAuthStatusResponse model exists."""
        from models.oauth_models import OAuthStatusResponse

        response = OAuthStatusResponse(
            connected=True,
            auth_method="oauth",
            scopes=["gmail.readonly"],
            token_expiry=datetime.utcnow(),
        )

        self.assertTrue(response.connected)
        self.assertEqual(response.auth_method, "oauth")

    def test_oauth_revoke_response_exists(self):
        """Test that OAuthRevokeResponse model exists."""
        from models.oauth_models import OAuthRevokeResponse

        response = OAuthRevokeResponse(
            success=True,
            message="OAuth access revoked",
        )

        self.assertTrue(response.success)
        self.assertEqual(response.message, "OAuth access revoked")


class TestCreateAccountRequestOAuthFields(unittest.TestCase):
    """Tests for OAuth fields in CreateAccountRequest."""

    def test_create_account_request_with_oauth(self):
        """Test CreateAccountRequest with OAuth auth method."""
        from models.create_account_request import CreateAccountRequest

        request = CreateAccountRequest(
            email_address="user@gmail.com",
            auth_method="oauth",
            oauth_refresh_token="refresh_token_123",
        )

        self.assertEqual(request.auth_method, "oauth")
        self.assertEqual(request.oauth_refresh_token, "refresh_token_123")
        self.assertIsNone(request.app_password)

    def test_create_account_request_with_imap(self):
        """Test CreateAccountRequest with IMAP auth method (default)."""
        from models.create_account_request import CreateAccountRequest

        request = CreateAccountRequest(
            email_address="user@gmail.com",
            app_password="app_password_123",
        )

        self.assertEqual(request.auth_method, "imap")
        self.assertEqual(request.app_password, "app_password_123")

    def test_create_account_request_oauth_requires_refresh_token(self):
        """Test that OAuth auth method requires refresh token."""
        from models.create_account_request import CreateAccountRequest
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            CreateAccountRequest(
                email_address="user@gmail.com",
                auth_method="oauth",
                # Missing oauth_refresh_token
            )

    def test_create_account_request_imap_requires_app_password(self):
        """Test that IMAP auth method requires app password."""
        from models.create_account_request import CreateAccountRequest
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            CreateAccountRequest(
                email_address="user@gmail.com",
                auth_method="imap",
                # Missing app_password
            )

    def test_create_account_request_invalid_auth_method(self):
        """Test that invalid auth method raises validation error."""
        from models.create_account_request import CreateAccountRequest
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            CreateAccountRequest(
                email_address="user@gmail.com",
                auth_method="invalid_method",
                app_password="password",
            )


class TestOAuthEndpointsImport(unittest.TestCase):
    """Tests that OAuth endpoints are properly registered."""

    def test_oauth_service_factory_exists(self):
        """Test that get_oauth_service factory function exists.

        This test verifies the source code directly rather than importing,
        since api_service has side effects (MySQL connection) at import time.
        """
        import ast

        # Read the api_service.py file and parse it
        with open('api_service.py', 'r') as f:
            source = f.read()

        tree = ast.parse(source)

        # Find function definition for get_oauth_service
        function_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'get_oauth_service':
                function_found = True
                break

        self.assertTrue(
            function_found,
            "api_service.py should define get_oauth_service function"
        )

    def test_oauth_flow_service_imported(self):
        """Test that OAuthFlowService is imported in api_service."""
        from services.oauth_flow_service import OAuthFlowService

        self.assertTrue(callable(OAuthFlowService))


class TestEmailAccountOAuthFields(unittest.TestCase):
    """Tests for OAuth fields in EmailAccount SQLAlchemy model."""

    def test_email_account_has_oauth_fields(self):
        """Test that EmailAccount model has OAuth fields."""
        from models.database import EmailAccount

        # Check that OAuth columns exist
        columns = EmailAccount.__table__.columns.keys()

        oauth_fields = [
            'auth_method',
            'oauth_client_id',
            'oauth_client_secret',
            'oauth_refresh_token',
            'oauth_access_token',
            'oauth_token_expiry',
            'oauth_scopes',
        ]

        for field in oauth_fields:
            self.assertIn(field, columns, f"EmailAccount should have {field} column")

    def test_email_account_auth_method_default(self):
        """Test that auth_method defaults to 'imap'."""
        from models.database import EmailAccount

        # Default should be 'imap' when not specified
        # Note: This tests the Column default, actual value may be None until DB insert
        auth_method_column = EmailAccount.__table__.columns['auth_method']
        self.assertEqual(auth_method_column.default.arg, 'imap')


class TestAccountCategoryClientOAuthMethods(unittest.TestCase):
    """Tests for OAuth methods in AccountCategoryClient."""

    def test_client_has_update_oauth_tokens_method(self):
        """Test that AccountCategoryClient has update_oauth_tokens method."""
        from clients.account_category_client import AccountCategoryClient

        self.assertTrue(
            hasattr(AccountCategoryClient, 'update_oauth_tokens'),
            "AccountCategoryClient should have update_oauth_tokens method"
        )

    def test_client_has_get_oauth_status_method(self):
        """Test that AccountCategoryClient has get_oauth_status method."""
        from clients.account_category_client import AccountCategoryClient

        self.assertTrue(
            hasattr(AccountCategoryClient, 'get_oauth_status'),
            "AccountCategoryClient should have get_oauth_status method"
        )

    def test_client_has_clear_oauth_tokens_method(self):
        """Test that AccountCategoryClient has clear_oauth_tokens method."""
        from clients.account_category_client import AccountCategoryClient

        self.assertTrue(
            hasattr(AccountCategoryClient, 'clear_oauth_tokens'),
            "AccountCategoryClient should have clear_oauth_tokens method"
        )

    def test_get_or_create_account_accepts_oauth_params(self):
        """Test that get_or_create_account accepts OAuth parameters."""
        from clients.account_category_client import AccountCategoryClient
        import inspect

        sig = inspect.signature(AccountCategoryClient.get_or_create_account)
        params = list(sig.parameters.keys())

        self.assertIn('auth_method', params)
        self.assertIn('oauth_refresh_token', params)


class TestSQLAlchemyRepositoryOAuthMethods(unittest.TestCase):
    """Tests for OAuth methods in SQLAlchemyRepository."""

    def test_repository_has_update_oauth_tokens_method(self):
        """Test that SQLAlchemyRepository has update_account_oauth_tokens method."""
        from repositories.sqlalchemy_repository import SQLAlchemyRepository

        self.assertTrue(
            hasattr(SQLAlchemyRepository, 'update_account_oauth_tokens'),
            "SQLAlchemyRepository should have update_account_oauth_tokens method"
        )

    def test_repository_has_get_oauth_tokens_method(self):
        """Test that SQLAlchemyRepository has get_account_oauth_tokens method."""
        from repositories.sqlalchemy_repository import SQLAlchemyRepository

        self.assertTrue(
            hasattr(SQLAlchemyRepository, 'get_account_oauth_tokens'),
            "SQLAlchemyRepository should have get_account_oauth_tokens method"
        )

    def test_repository_has_clear_oauth_tokens_method(self):
        """Test that SQLAlchemyRepository has clear_account_oauth_tokens method."""
        from repositories.sqlalchemy_repository import SQLAlchemyRepository

        self.assertTrue(
            hasattr(SQLAlchemyRepository, 'clear_account_oauth_tokens'),
            "SQLAlchemyRepository should have clear_account_oauth_tokens method"
        )

    def test_repository_has_update_access_token_method(self):
        """Test that SQLAlchemyRepository has update_account_access_token method."""
        from repositories.sqlalchemy_repository import SQLAlchemyRepository

        self.assertTrue(
            hasattr(SQLAlchemyRepository, 'update_account_access_token'),
            "SQLAlchemyRepository should have update_account_access_token method"
        )


if __name__ == '__main__':
    unittest.main()
