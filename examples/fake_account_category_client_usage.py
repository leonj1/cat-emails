"""
Example usage of FakeAccountCategoryClient for testing.

This demonstrates how to use the fake implementation of AccountCategoryClientInterface
in your tests instead of relying on a real database.
"""
from datetime import date
from tests.fake_account_category_client import FakeAccountCategoryClient


def example_usage():
    """Demonstrate using the fake client."""

    # Create the fake client
    client = FakeAccountCategoryClient()

    # Create some accounts
    account1 = client.get_or_create_account("user1@example.com", "User One")
    account2 = client.get_or_create_account("user2@example.com", "User Two")

    print(f"Created account: {account1.email_address} (ID: {account1.id})")
    print(f"Created account: {account2.email_address} (ID: {account2.id})")

    # Update last scan
    client.update_account_last_scan("user1@example.com")

    # Record category statistics
    stats_date = date.today()
    category_stats = {
        "Marketing": {"total": 100, "deleted": 80, "kept": 20, "archived": 0},
        "Personal": {"total": 50, "deleted": 0, "kept": 50, "archived": 0},
        "Work": {"total": 75, "deleted": 10, "kept": 60, "archived": 5}
    }

    client.record_category_stats("user1@example.com", stats_date, category_stats)
    print(f"\nRecorded category stats for user1@example.com")

    # Get top categories
    response = client.get_top_categories("user1@example.com", days=30, limit=10, include_counts=True)

    print(f"\nTop categories for {response.email_address}:")
    print(f"Period: {response.period.start_date} to {response.period.end_date} ({response.period.days} days)")
    print(f"Total emails: {response.total_emails}")
    print("\nCategories:")

    for category in response.top_categories:
        print(f"  - {category.category}: {category.total_count} emails ({category.percentage}%)")
        if category.kept_count is not None:
            print(f"    Kept: {category.kept_count}, Deleted: {category.deleted_count}, Archived: {category.archived_count}")

    # Get all accounts
    all_accounts = client.get_all_accounts(active_only=True)
    print(f"\nActive accounts: {len(all_accounts)}")
    for acc in all_accounts:
        print(f"  - {acc.email_address}")

    # Deactivate an account
    client.deactivate_account("user2@example.com")
    print(f"\nDeactivated user2@example.com")

    # Get active accounts again
    active_accounts = client.get_all_accounts(active_only=True)
    print(f"Active accounts after deactivation: {len(active_accounts)}")


if __name__ == "__main__":
    example_usage()
