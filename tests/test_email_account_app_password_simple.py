#!/usr/bin/env python3
"""
Simple test to verify EmailAccount has app_password attribute.

This test would have caught the AttributeError: 'EmailAccount' object has no attribute 'app_password'
"""
import unittest
import tempfile
import os
from faker import Faker

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import init_database, get_session, EmailAccount


class TestEmailAccountAppPasswordField(unittest.TestCase):
    """Test that EmailAccount model has app_password field."""

    def setUp(self):
        """Set up test database."""
        self.fake = Faker()

        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize database
        self.engine = init_database(self.temp_db_path)
        self.session = get_session(self.engine)

    def tearDown(self):
        """Clean up test database."""
        self.session.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_email_account_has_app_password_field(self):
        """Test that EmailAccount can store and retrieve app_password."""
        # Generate random test data
        test_email = self.fake.email()
        test_password = self.fake.password()
        display_name = self.fake.name()

        # Create EmailAccount with app_password
        account = EmailAccount(
            email_address=test_email,
            app_password=test_password,
            display_name=display_name
        )

        # This should NOT raise AttributeError
        self.assertEqual(account.app_password, test_password)

        # Save to database
        self.session.add(account)
        self.session.commit()

        # Retrieve from database
        retrieved = self.session.query(EmailAccount).filter_by(
            email_address=test_email
        ).first()

        # Verify app_password was persisted
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.app_password, test_password)
        self.assertEqual(retrieved.email_address, test_email)
        self.assertEqual(retrieved.display_name, display_name)

    def test_app_password_can_be_none(self):
        """Test that app_password can be None (nullable)."""
        # Generate random test data
        test_email = self.fake.email()

        # Create EmailAccount without app_password
        account = EmailAccount(
            email_address=test_email,
            app_password=None  # Explicitly set to None
        )

        # Save to database
        self.session.add(account)
        self.session.commit()

        # Retrieve from database
        retrieved = self.session.query(EmailAccount).filter_by(
            email_address=test_email
        ).first()

        # Verify app_password is None
        self.assertIsNotNone(retrieved)
        self.assertIsNone(retrieved.app_password)

    def test_app_password_attribute_exists(self):
        """Test that EmailAccount has app_password attribute (not just column)."""
        # Generate random test email
        test_email = self.fake.email()

        # Create EmailAccount
        account = EmailAccount(email_address=test_email)

        # This should NOT raise AttributeError
        # Even if not set, the attribute should exist
        self.assertTrue(hasattr(account, 'app_password'))

        # Should be able to access it without error
        app_pwd = account.app_password  # Should not raise AttributeError
        self.assertIsNone(app_pwd)  # Default should be None


if __name__ == '__main__':
    unittest.main()