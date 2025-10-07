#!/usr/bin/env python3
"""
Example showing how masked passwords appear in the API response
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.password_utils import mask_password


def simulate_api_response():
    """Simulate what the API response would look like"""

    # Sample accounts with different password scenarios
    accounts = [
        {
            "email": "user1@gmail.com",
            "password": "abcd1234wxyz5678",  # 16 char app password
            "display_name": "User One"
        },
        {
            "email": "user2@gmail.com",
            "password": None,  # No password configured
            "display_name": "User Two"
        },
        {
            "email": "user3@gmail.com",
            "password": "shortpwd",  # Shorter password
            "display_name": "User Three"
        },
        {
            "email": "user4@gmail.com",
            "password": "verylongpassword12345",  # Long password
            "display_name": "User Four"
        }
    ]

    print("Simulated API Response for GET /api/accounts")
    print("=" * 60)
    print()
    print("Response JSON:")
    print("{")
    print('  "accounts": [')

    for i, account in enumerate(accounts):
        masked_pwd = mask_password(account["password"])
        masked_display = f'"{masked_pwd}"' if masked_pwd else "null"

        print("    {")
        print(f'      "id": {i+1},')
        print(f'      "email_address": "{account["email"]}",')
        print(f'      "display_name": "{account["display_name"]}",')
        print(f'      "masked_password": {masked_display},')
        print(f'      "is_active": true,')
        print(f'      "last_scan_at": "2024-01-15T10:30:00Z",')
        print(f'      "created_at": "2024-01-01T00:00:00Z"')

        if i < len(accounts) - 1:
            print("    },")
        else:
            print("    }")

    print("  ],")
    print(f'  "total_count": {len(accounts)}')
    print("}")

    print()
    print("=" * 60)
    print("Password Status Interpretation:")
    print()

    for account in accounts:
        email = account["email"]
        masked = mask_password(account["password"])

        if masked is None:
            print(f"❌ {email}: No password configured")
        elif len(masked) == 16 and masked.count("*") == 12:
            print(f"✅ {email}: Standard 16-char app password ({masked})")
        else:
            print(f"⚠️  {email}: Non-standard password ({masked})")

    print()
    print("Notes:")
    print("- Gmail app passwords are typically 16 characters")
    print("- Masked format shows: first 2 chars + asterisks + last 2 chars")
    print("- null means no password is configured")
    print("- This helps quickly identify accounts with missing/invalid passwords")


if __name__ == "__main__":
    simulate_api_response()