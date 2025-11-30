"""
Test suite for FeatureFlags dataclass.

Tests the parsing of SEND_LOGS environment variable from a dictionary.
Following TDD Red phase - these tests will fail until implementation exists.

The implementation should:
- Create a frozen dataclass FeatureFlags with send_logs: bool attribute
- Provide a from_environment(cls, env_vars: dict) class method
- Parse SEND_LOGS env var: truthy values ("true", "True", "TRUE", "1", "yes", "Yes", "YES") -> True
- All other values (including missing, empty, "false", "0", "no", invalid strings) -> False
"""
import unittest


class TestFeatureFlagsFromEnvironment(unittest.TestCase):
    """Test cases for FeatureFlags.from_environment() class method."""

    def test_send_logs_missing_defaults_to_false(self):
        """
        Scenario: SEND_LOGS environment variable missing defaults to False

        Given the SEND_LOGS environment variable is not set
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertIsInstance(flags, FeatureFlags)
        self.assertFalse(flags.send_logs, "Missing SEND_LOGS should default to False")

    def test_send_logs_empty_string_defaults_to_false(self):
        """
        Scenario: SEND_LOGS environment variable is empty string defaults to False

        Given the SEND_LOGS environment variable is set to ""
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": ""}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertIsInstance(flags, FeatureFlags)
        self.assertFalse(flags.send_logs, "Empty SEND_LOGS should default to False")


class TestFeatureFlagsTruthyValues(unittest.TestCase):
    """Test cases for truthy SEND_LOGS values."""

    def test_send_logs_lowercase_true(self):
        """
        Scenario: SEND_LOGS truthy value 'true' parsed correctly

        Given the SEND_LOGS environment variable is set to "true"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True
        """
        # Arrange
        env_vars = {"SEND_LOGS": "true"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS='true' should be True")

    def test_send_logs_capitalized_true(self):
        """
        Scenario: SEND_LOGS truthy value 'True' parsed correctly

        Given the SEND_LOGS environment variable is set to "True"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True
        """
        # Arrange
        env_vars = {"SEND_LOGS": "True"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS='True' should be True")

    def test_send_logs_uppercase_true(self):
        """
        Scenario: SEND_LOGS truthy value 'TRUE' parsed correctly

        Given the SEND_LOGS environment variable is set to "TRUE"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True
        """
        # Arrange
        env_vars = {"SEND_LOGS": "TRUE"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS='TRUE' should be True")

    def test_send_logs_numeric_one(self):
        """
        Scenario: SEND_LOGS truthy value '1' parsed correctly

        Given the SEND_LOGS environment variable is set to "1"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True
        """
        # Arrange
        env_vars = {"SEND_LOGS": "1"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS='1' should be True")

    def test_send_logs_lowercase_yes(self):
        """
        Scenario: SEND_LOGS truthy value 'yes' parsed correctly

        Given the SEND_LOGS environment variable is set to "yes"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True
        """
        # Arrange
        env_vars = {"SEND_LOGS": "yes"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS='yes' should be True")

    def test_send_logs_capitalized_yes(self):
        """
        Scenario: SEND_LOGS truthy value 'Yes' parsed correctly

        Given the SEND_LOGS environment variable is set to "Yes"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True
        """
        # Arrange
        env_vars = {"SEND_LOGS": "Yes"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS='Yes' should be True")

    def test_send_logs_uppercase_yes(self):
        """
        Scenario: SEND_LOGS truthy value 'YES' parsed correctly

        Given the SEND_LOGS environment variable is set to "YES"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True
        """
        # Arrange
        env_vars = {"SEND_LOGS": "YES"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS='YES' should be True")


class TestFeatureFlagsFalsyValues(unittest.TestCase):
    """Test cases for falsy SEND_LOGS values."""

    def test_send_logs_lowercase_false(self):
        """
        Scenario: SEND_LOGS falsy value 'false' parsed correctly

        Given the SEND_LOGS environment variable is set to "false"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "false"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='false' should be False")

    def test_send_logs_capitalized_false(self):
        """
        Scenario: SEND_LOGS falsy value 'False' parsed correctly

        Given the SEND_LOGS environment variable is set to "False"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "False"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='False' should be False")

    def test_send_logs_uppercase_false(self):
        """
        Scenario: SEND_LOGS falsy value 'FALSE' parsed correctly

        Given the SEND_LOGS environment variable is set to "FALSE"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "FALSE"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='FALSE' should be False")

    def test_send_logs_numeric_zero(self):
        """
        Scenario: SEND_LOGS falsy value '0' parsed correctly

        Given the SEND_LOGS environment variable is set to "0"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "0"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='0' should be False")

    def test_send_logs_lowercase_no(self):
        """
        Scenario: SEND_LOGS falsy value 'no' parsed correctly

        Given the SEND_LOGS environment variable is set to "no"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "no"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='no' should be False")

    def test_send_logs_capitalized_no(self):
        """
        Scenario: SEND_LOGS falsy value 'No' parsed correctly

        Given the SEND_LOGS environment variable is set to "No"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "No"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='No' should be False")

    def test_send_logs_uppercase_no(self):
        """
        Scenario: SEND_LOGS falsy value 'NO' parsed correctly

        Given the SEND_LOGS environment variable is set to "NO"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "NO"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='NO' should be False")

    def test_send_logs_random_string(self):
        """
        Scenario: SEND_LOGS falsy value 'random' parsed correctly

        Given the SEND_LOGS environment variable is set to "random"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "random"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='random' should be False")

    def test_send_logs_invalid_string(self):
        """
        Scenario: SEND_LOGS falsy value 'invalid' parsed correctly

        Given the SEND_LOGS environment variable is set to "invalid"
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "invalid"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='invalid' should be False")


class TestFeatureFlagsImmutability(unittest.TestCase):
    """Test cases for FeatureFlags immutability (frozen dataclass)."""

    def test_feature_flags_is_frozen(self):
        """
        Test that FeatureFlags is immutable (frozen dataclass).

        The implementation should:
        - Be a frozen dataclass
        - Raise FrozenInstanceError when attempting to modify attributes
        """
        # Arrange
        env_vars = {"SEND_LOGS": "true"}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert - attempting to modify should raise an exception
        with self.assertRaises(Exception):
            flags.send_logs = False


class TestFeatureFlagsEdgeCases(unittest.TestCase):
    """Test cases for edge cases in SEND_LOGS parsing."""

    def test_send_logs_with_whitespace_true(self):
        """
        Test that whitespace around truthy value is handled correctly.

        Given the SEND_LOGS environment variable is set to " true "
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True (after stripping whitespace)
        """
        # Arrange
        env_vars = {"SEND_LOGS": " true "}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS=' true ' should be True after stripping")

    def test_send_logs_with_whitespace_yes(self):
        """
        Test that whitespace around 'yes' value is handled correctly.

        Given the SEND_LOGS environment variable is set to "  yes  "
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True (after stripping whitespace)
        """
        # Arrange
        env_vars = {"SEND_LOGS": "  yes  "}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS='  yes  ' should be True after stripping")

    def test_send_logs_with_whitespace_one(self):
        """
        Test that whitespace around '1' value is handled correctly.

        Given the SEND_LOGS environment variable is set to " 1 "
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be True (after stripping whitespace)
        """
        # Arrange
        env_vars = {"SEND_LOGS": " 1 "}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertTrue(flags.send_logs, "SEND_LOGS=' 1 ' should be True after stripping")

    def test_send_logs_whitespace_only_defaults_to_false(self):
        """
        Test that whitespace-only value defaults to False.

        Given the SEND_LOGS environment variable is set to "   "
        When the FeatureFlags are loaded from the environment
        Then the send_logs flag should be False
        """
        # Arrange
        env_vars = {"SEND_LOGS": "   "}

        # Act
        from models.feature_flags import FeatureFlags
        flags = FeatureFlags.from_environment(env_vars)

        # Assert
        self.assertFalse(flags.send_logs, "SEND_LOGS='   ' should be False")


if __name__ == '__main__':
    unittest.main()
