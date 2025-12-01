Feature: Remove Logs Collector Phase 1 - Delete Core Service Files
  As a maintainer
  I want to remove the centralized logs collector infrastructure
  So that the codebase is simplified and unnecessary dependencies are eliminated

  Background:
    Given the codebase is under version control

  Scenario: Logs collector service file is deleted
    When the logs collector removal phase 1 is complete
    Then the file "services/logs_collector_service.py" should not exist

  Scenario: Logs collector interface file is deleted
    When the logs collector removal phase 1 is complete
    Then the file "services/logs_collector_interface.py" should not exist

  Scenario: Logs collector client file is deleted
    When the logs collector removal phase 1 is complete
    Then the file "clients/logs_collector_client.py" should not exist

  Scenario: Central logging service files are deleted
    When the logs collector removal phase 1 is complete
    Then the file "services/logging_service.py" should not exist
    And the file "services/logging_factory.py" should not exist
