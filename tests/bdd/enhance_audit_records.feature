Feature: Enhance Audit Records with Categorized and Skipped Email Counts
  As a system administrator
  I want audit records to track how many emails were categorized and skipped
  So that I can monitor processing effectiveness and identify potential issues

  Background:
    Given the email processing system is running
    And audit logging is enabled

  # Database Model Scenarios
  Scenario: Audit record contains emails_categorized field
    Given a processing session has started
    When the session completes processing
    Then the audit record should contain an emails_categorized field
    And the emails_categorized field should be a non-negative integer

  Scenario: Audit record contains emails_skipped field
    Given a processing session has started
    When the session completes processing
    Then the audit record should contain an emails_skipped field
    And the emails_skipped field should be a non-negative integer

  # Increment Methods Scenarios
  Scenario: Categorized count increments when email is successfully categorized
    Given a processing session has started
    And the emails_categorized count is 0
    When an email is successfully categorized
    Then the emails_categorized count should be 1

  Scenario: Skipped count increments when email is skipped
    Given a processing session has started
    And the emails_skipped count is 0
    When an email is skipped due to processing rules
    Then the emails_skipped count should be 1

  Scenario: Multiple emails increment counts correctly
    Given a processing session has started
    And 5 emails are successfully categorized
    And 3 emails are skipped
    When the session audit is retrieved
    Then the emails_categorized count should be 5
    And the emails_skipped count should be 3

  # Complete Processing Flow Scenarios
  Scenario: Audit record reflects complete processing batch
    Given a processing session has started
    And a batch of 10 emails is submitted for processing
    When 7 emails are categorized successfully
    And 3 emails are skipped
    Then the final audit record should show emails_categorized as 7
    And the final audit record should show emails_skipped as 3

  Scenario: Audit record persists after session completion
    Given a processing session has completed
    And the session categorized 15 emails
    And the session skipped 5 emails
    When the audit record is retrieved later
    Then the emails_categorized should still be 15
    And the emails_skipped should still be 5

  # API Response Scenarios
  Scenario: Audit summary endpoint returns categorized count
    Given audit records exist with categorized emails
    When the audit summary is requested
    Then the response should include the emails_categorized count

  Scenario: Audit summary endpoint returns skipped count
    Given audit records exist with skipped emails
    When the audit summary is requested
    Then the response should include the emails_skipped count

  # Zero Counts Edge Cases
  Scenario: Audit record handles zero categorized emails
    Given a processing session has started
    When all emails in the batch are skipped
    Then the emails_categorized count should be 0
    And the emails_skipped count should match the batch size

  Scenario: Audit record handles zero skipped emails
    Given a processing session has started
    When all emails in the batch are categorized successfully
    Then the emails_skipped count should be 0
    And the emails_categorized count should match the batch size

  Scenario: Audit record handles empty batch
    Given a processing session has started
    When an empty batch is processed
    Then the emails_categorized count should be 0
    And the emails_skipped count should be 0

  Scenario: New audit record initializes counts to zero
    Given no processing has occurred
    When a new processing session begins
    Then the initial emails_categorized count should be 0
    And the initial emails_skipped count should be 0

  # No Active Session Edge Cases
  Scenario: System handles increment without active session gracefully
    Given no processing session is active
    When an attempt is made to increment categorized count
    Then the system should handle the situation gracefully
    And no error should be raised

  Scenario: System logs warning when incrementing without session
    Given no processing session is active
    When an attempt is made to increment skipped count
    Then a warning should be logged
    And the increment should be ignored

  # Large Counts Edge Cases
  Scenario: Audit record handles large categorized counts
    Given a processing session has started
    When 100000 emails are categorized
    Then the emails_categorized count should be 100000
    And the count should be stored accurately

  Scenario: Audit record handles large skipped counts
    Given a processing session has started
    When 100000 emails are skipped
    Then the emails_skipped count should be 100000
    And the count should be stored accurately

  # Database Migration Scenarios
  Scenario: Existing audit records receive default values after migration
    Given audit records exist from before the enhancement
    When the database migration is applied
    Then existing records should have emails_categorized defaulted to 0
    And existing records should have emails_skipped defaulted to 0

  Scenario: New audit records work correctly after migration
    Given the database migration has been applied
    When a new processing session creates an audit record
    Then the emails_categorized field should be available
    And the emails_skipped field should be available
    And both fields should accept increments

  # Thread Safety Scenarios
  Scenario: Concurrent categorization increments are handled correctly
    Given a processing session has started
    When multiple emails are categorized simultaneously
    Then all increments should be recorded
    And the final count should reflect all categorizations

  Scenario: Concurrent skip increments are handled correctly
    Given a processing session has started
    When multiple emails are skipped simultaneously
    Then all increments should be recorded
    And the final count should reflect all skips

  # Data Integrity Scenarios
  Scenario: Categorized and skipped counts sum correctly
    Given a processing session has started
    And 100 emails are in the batch
    When processing completes with 60 categorized and 40 skipped
    Then the sum of emails_categorized and emails_skipped should equal 100

  Scenario: Audit record maintains count accuracy across restarts
    Given a processing session has recorded 50 categorized and 20 skipped
    When the system restarts
    And the audit record is retrieved
    Then the emails_categorized should be 50
    And the emails_skipped should be 20
