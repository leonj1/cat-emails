Feature: SEND_LOGS Feature Flag
  As a system administrator
  I want to control whether logs are sent to a remote location
  So that I can enable or disable log transmission based on environment requirements

  Background:
    Given the application uses a LogsCollectorService for log management

  # ==========================================
  # Constructor Requirements
  # ==========================================

  Scenario: LogsCollectorService requires send_logs parameter
    When I instantiate LogsCollectorService without the send_logs parameter
    Then a TypeError should be raised
    And the error message should indicate send_logs is a required argument

  Scenario: LogsCollectorService accepts send_logs=True
    When I instantiate LogsCollectorService with send_logs=True
    Then the service should be created successfully
    And the is_send_enabled property should return True

  Scenario: LogsCollectorService accepts send_logs=False
    When I instantiate LogsCollectorService with send_logs=False
    Then the service should be created successfully
    And the is_send_enabled property should return False

  # ==========================================
  # Environment Variable Parsing
  # ==========================================

  Scenario: SEND_LOGS environment variable missing defaults to False
    Given the SEND_LOGS environment variable is not set
    When the FeatureFlags are loaded from the environment
    Then the send_logs flag should be False

  Scenario: SEND_LOGS environment variable is empty string defaults to False
    Given the SEND_LOGS environment variable is set to ""
    When the FeatureFlags are loaded from the environment
    Then the send_logs flag should be False

  Scenario Outline: SEND_LOGS truthy values are parsed correctly
    Given the SEND_LOGS environment variable is set to "<value>"
    When the FeatureFlags are loaded from the environment
    Then the send_logs flag should be True

    Examples:
      | value |
      | true  |
      | True  |
      | TRUE  |
      | 1     |
      | yes   |
      | Yes   |
      | YES   |

  Scenario Outline: SEND_LOGS falsy values are parsed correctly
    Given the SEND_LOGS environment variable is set to "<value>"
    When the FeatureFlags are loaded from the environment
    Then the send_logs flag should be False

    Examples:
      | value   |
      | false   |
      | False   |
      | FALSE   |
      | 0       |
      | no      |
      | No      |
      | NO      |
      | random  |
      | invalid |

  # ==========================================
  # Log Sending Behavior
  # ==========================================

  Scenario: Logs are transmitted when send_logs is True and API is configured
    Given a LogsCollectorService with send_logs=True
    And the LOGS_API_URL is configured
    And the LOGS_API_TOKEN is configured
    When a log entry is collected and flushed
    Then the log should be transmitted to the remote API

  Scenario: Logs are suppressed when send_logs is False
    Given a LogsCollectorService with send_logs=False
    And the LOGS_API_URL is configured
    When a log entry is collected and flushed
    Then the log should NOT be transmitted to the remote API
    And a debug message should indicate log sending is disabled

  Scenario: Logs are suppressed when API URL is not configured
    Given a LogsCollectorService with send_logs=True
    And the LOGS_API_URL is NOT configured
    When a log entry is collected and flushed
    Then the log should NOT be transmitted
    And a debug message should indicate no API URL is configured

  Scenario: Flush returns False when sending is disabled
    Given a LogsCollectorService with send_logs=False
    When flush() is called
    Then the return value should be False

  Scenario: Flush returns True when sending succeeds
    Given a LogsCollectorService with send_logs=True
    And the API is configured and accessible
    And there are collected logs
    When flush() is called
    Then the return value should be True
    And the collected logs should be cleared

  # ==========================================
  # Service Dependency Injection
  # ==========================================

  Scenario: EmailProcessorService receives ILogsCollector via constructor
    Given a LogsCollectorService configured with send_logs=True
    When EmailProcessorService is instantiated with the logs collector
    Then the service should use the provided logs collector
    And the service should NOT create its own LogsCollectorService

  Scenario: EmailSummaryService receives ILogsCollector via constructor
    Given a LogsCollectorService configured with send_logs=False
    When EmailSummaryService is instantiated with the logs collector
    Then the service should use the provided logs collector
    And the service should NOT create its own LogsCollectorService

  Scenario: AccountEmailProcessorService receives ILogsCollector via constructor
    Given a LogsCollectorService configured with send_logs=True
    When AccountEmailProcessorService is instantiated with the logs collector
    Then the service should use the provided logs collector
    And the service should NOT create its own LogsCollectorService

  # ==========================================
  # API Service Integration (api_service.py)
  # ==========================================

  Scenario: API service reads SEND_LOGS at startup
    Given the SEND_LOGS environment variable is set to "true"
    When the FastAPI application starts
    Then the FeatureFlags should be created with send_logs=True
    And the LogsCollectorService should be created with send_logs=True

  Scenario: API service propagates send_logs through service chain
    Given the SEND_LOGS environment variable is set to "true"
    When the FastAPI application starts
    And dependent services are initialized
    Then all services should share the same LogsCollectorService instance
    And that instance should have send_logs=True

  Scenario: API service defaults send_logs to False when env var missing
    Given the SEND_LOGS environment variable is not set
    When the FastAPI application starts
    Then the LogsCollectorService should be created with send_logs=False

  # ==========================================
  # Standalone Script Integration (gmail_fetcher.py)
  # ==========================================

  Scenario: gmail_fetcher reads SEND_LOGS at startup
    Given the SEND_LOGS environment variable is set to "true"
    When gmail_fetcher.py main() function is executed
    Then the LogsCollectorService should be created with send_logs=True

  Scenario: gmail_fetcher defaults send_logs to False when env var missing
    Given the SEND_LOGS environment variable is not set
    When gmail_fetcher.py main() function is executed
    Then the LogsCollectorService should be created with send_logs=False

  Scenario: gmail_fetcher creates LogsCollectorService with explicit flag
    Given the SEND_LOGS environment variable is set to "1"
    When gmail_fetcher.py initializes the LogsCollectorService
    Then the constructor receives send_logs=True as a required parameter
    And no default value is used

  # ==========================================
  # Constructor Argument Limit Compliance
  # ==========================================

  Scenario: LogsCollectorService has fewer than 4 constructor arguments
    When I inspect the LogsCollectorService constructor
    Then it should have at most 3 parameters (excluding self)
    And send_logs should be the first required parameter

  Scenario: Services maintain constructor argument limit
    When I inspect all service constructors that use ILogsCollector
    Then each service should have fewer than 4 parameters (excluding self)

  # ==========================================
  # Error Handling
  # ==========================================

  Scenario: LogsCollectorService handles API transmission errors gracefully
    Given a LogsCollectorService with send_logs=True
    And the LOGS_API_URL points to an unreachable endpoint
    When a log entry is collected and flushed
    Then the flush should return False
    And an error should be logged

  Scenario: LogsCollectorService clears collected logs after successful transmission
    Given a LogsCollectorService with send_logs=True
    And multiple log entries have been collected
    When flush() succeeds
    Then the internal log buffer should be empty

  Scenario: LogsCollectorService retains logs after failed transmission
    Given a LogsCollectorService with send_logs=True
    And multiple log entries have been collected
    When flush() fails due to API error
    Then the internal log buffer should NOT be cleared
