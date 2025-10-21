"""
Example class with large functions for testing the refactoring agent.

This class intentionally has multiple functions that exceed 30 lines
to demonstrate the refactoring agent's capabilities.
"""

import os
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime


class UserDataProcessor:
    """
    A service that processes user data from various sources.

    This class has multiple responsibilities and large functions that
    should be extracted into separate service classes.
    """

    def __init__(self):
        """Initialize the processor"""
        self.processed_count = 0
        self.errors = []

    def process_user_data(self, user_id: str) -> Dict:
        """
        Main function that processes user data (PRIMARY FUNCTION).

        This is intentionally large to demonstrate refactoring.
        """
        print(f"Processing user data for {user_id}")

        # Fetch user from API
        user = self.fetch_user_from_api(user_id)
        if not user:
            return {"error": "User not found"}

        # Validate user data
        is_valid = self.validate_user_data(user)
        if not is_valid:
            return {"error": "Invalid user data"}

        # Enrich user data
        enriched = self.enrich_user_data(user)

        # Store in database
        stored = self.store_user_data(enriched)

        # Send notification
        self.send_notification(user_id, "processed")

        # Update metrics
        self.processed_count += 1

        # Generate report
        report = self.generate_user_report(enriched)

        return {
            "success": True,
            "user_id": user_id,
            "processed_at": datetime.now().isoformat(),
            "report": report
        }

    def fetch_user_from_api(self, user_id: str) -> Optional[Dict]:
        """
        Fetch user data from external API.

        This function has multiple issues:
        - Direct environment variable access (BAD)
        - Creates HTTP client directly (BAD)
        - Exceeds 30 lines (SHOULD BE EXTRACTED)
        """
        # BAD: Direct env var access
        api_url = os.getenv("USER_API_URL", "https://api.example.com")
        api_key = os.getenv("USER_API_KEY", "default_key")

        # BAD: Creates client directly
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {api_key}"})

        try:
            # Fetch user
            response = session.get(f"{api_url}/users/{user_id}")
            response.raise_for_status()

            user_data = response.json()

            # Fetch additional details
            details_response = session.get(f"{api_url}/users/{user_id}/details")
            if details_response.status_code == 200:
                user_data["details"] = details_response.json()

            # Fetch user preferences
            prefs_response = session.get(f"{api_url}/users/{user_id}/preferences")
            if prefs_response.status_code == 200:
                user_data["preferences"] = prefs_response.json()

            # Log the fetch
            print(f"Successfully fetched user {user_id}")

            return user_data

        except requests.RequestException as e:
            print(f"Error fetching user {user_id}: {e}")
            self.errors.append(str(e))
            return None
        finally:
            session.close()

    def validate_user_data(self, user: Dict) -> bool:
        """
        Validate user data structure and content.

        This function exceeds 30 lines and should be extracted.
        """
        # Check required fields
        required_fields = ["id", "email", "name", "created_at"]
        for field in required_fields:
            if field not in user:
                print(f"Missing required field: {field}")
                return False

        # Validate email format
        email = user.get("email", "")
        if "@" not in email or "." not in email:
            print(f"Invalid email format: {email}")
            return False

        # Validate name
        name = user.get("name", "")
        if len(name) < 2:
            print(f"Name too short: {name}")
            return False

        # Validate creation date
        try:
            datetime.fromisoformat(user["created_at"])
        except (ValueError, TypeError):
            print(f"Invalid created_at date: {user.get('created_at')}")
            return False

        # Validate optional fields if present
        if "age" in user:
            age = user["age"]
            if not isinstance(age, int) or age < 0 or age > 150:
                print(f"Invalid age: {age}")
                return False

        if "phone" in user:
            phone = user["phone"]
            if not phone.replace("-", "").replace(" ", "").isdigit():
                print(f"Invalid phone: {phone}")
                return False

        print(f"User data validated successfully")
        return True

    def enrich_user_data(self, user: Dict) -> Dict:
        """
        Enrich user data with additional information.

        This function exceeds 30 lines and should be extracted.
        """
        enriched = user.copy()

        # Add processing metadata
        enriched["processed_at"] = datetime.now().isoformat()
        enriched["processor_version"] = "1.0.0"

        # Calculate derived fields
        if "created_at" in user:
            created = datetime.fromisoformat(user["created_at"])
            account_age_days = (datetime.now() - created).days
            enriched["account_age_days"] = account_age_days

            # Determine user tier based on account age
            if account_age_days > 365:
                enriched["tier"] = "premium"
            elif account_age_days > 90:
                enriched["tier"] = "standard"
            else:
                enriched["tier"] = "new"

        # Add geographic data if available
        if "country" in user:
            country = user["country"]
            enriched["region"] = self._get_region_for_country(country)
            enriched["timezone"] = self._get_timezone_for_country(country)

        # Add engagement score
        if "details" in user:
            details = user["details"]
            login_count = details.get("login_count", 0)
            purchase_count = details.get("purchase_count", 0)

            # Simple engagement calculation
            engagement_score = (login_count * 1) + (purchase_count * 10)
            enriched["engagement_score"] = engagement_score

            if engagement_score > 100:
                enriched["engagement_level"] = "high"
            elif engagement_score > 50:
                enriched["engagement_level"] = "medium"
            else:
                enriched["engagement_level"] = "low"

        print(f"User data enriched successfully")
        return enriched

    def store_user_data(self, user: Dict) -> bool:
        """
        Store user data in database.

        This function has issues:
        - Direct env var access (BAD)
        - Creates DB client directly (BAD)
        - Exceeds 30 lines (SHOULD BE EXTRACTED)
        """
        # BAD: Direct env var access
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = int(os.getenv("DB_PORT", "5432"))
        db_name = os.getenv("DB_NAME", "users")

        # BAD: This would create a DB client directly
        # db_client = DatabaseClient(host=db_host, port=db_port, database=db_name)

        try:
            # For this example, we'll just simulate storage
            print(f"Connecting to database at {db_host}:{db_port}/{db_name}")

            # Prepare data for storage
            user_id = user["id"]
            email = user["email"]
            name = user["name"]

            # Store main user record
            print(f"Storing user record for {user_id}")

            # Store enriched data
            if "engagement_score" in user:
                print(f"Storing engagement data for {user_id}")

            # Store preferences
            if "preferences" in user:
                print(f"Storing preferences for {user_id}")

            # Update search index
            print(f"Updating search index for {user_id}")

            # Invalidate cache
            print(f"Invalidating cache for {user_id}")

            print(f"Successfully stored user {user_id}")
            return True

        except Exception as e:
            print(f"Error storing user: {e}")
            self.errors.append(str(e))
            return False

    def send_notification(self, user_id: str, event: str) -> bool:
        """
        Send notification about user processing.

        This function exceeds 30 lines and should be extracted.
        """
        # BAD: Direct env var access
        notification_service = os.getenv("NOTIFICATION_SERVICE", "email")
        notification_url = os.getenv("NOTIFICATION_URL", "https://notify.example.com")

        # Prepare notification data
        notification_data = {
            "user_id": user_id,
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "source": "UserDataProcessor"
        }

        try:
            # BAD: Creates HTTP client directly
            response = requests.post(
                f"{notification_url}/send",
                json=notification_data,
                timeout=5
            )

            if response.status_code == 200:
                print(f"Notification sent for {user_id}")
                return True
            else:
                print(f"Failed to send notification: {response.status_code}")
                return False

        except requests.RequestException as e:
            print(f"Error sending notification: {e}")
            self.errors.append(str(e))
            return False

    def generate_user_report(self, user: Dict) -> Dict:
        """
        Generate a comprehensive user report.

        This function exceeds 30 lines and should be extracted.
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "user_id": user["id"],
            "summary": {}
        }

        # Basic info
        report["summary"]["name"] = user["name"]
        report["summary"]["email"] = user["email"]

        # Account info
        if "account_age_days" in user:
            report["summary"]["account_age_days"] = user["account_age_days"]
            report["summary"]["tier"] = user.get("tier", "unknown")

        # Engagement
        if "engagement_score" in user:
            report["summary"]["engagement_score"] = user["engagement_score"]
            report["summary"]["engagement_level"] = user.get("engagement_level", "unknown")

        # Geographic
        if "region" in user:
            report["summary"]["region"] = user["region"]
            report["summary"]["timezone"] = user.get("timezone", "UTC")

        # Preferences
        if "preferences" in user:
            prefs = user["preferences"]
            report["preferences"] = {
                "email_notifications": prefs.get("email_notifications", True),
                "sms_notifications": prefs.get("sms_notifications", False),
                "language": prefs.get("language", "en")
            }

        # Recommendations
        recommendations = []
        if user.get("engagement_level") == "low":
            recommendations.append("Consider sending engagement campaign")
        if user.get("tier") == "premium":
            recommendations.append("Eligible for premium features")

        report["recommendations"] = recommendations

        print(f"Report generated for {user['id']}")
        return report

    def _get_region_for_country(self, country: str) -> str:
        """Helper to map country to region"""
        region_map = {
            "US": "North America",
            "CA": "North America",
            "MX": "North America",
            "GB": "Europe",
            "FR": "Europe",
            "DE": "Europe",
        }
        return region_map.get(country, "Unknown")

    def _get_timezone_for_country(self, country: str) -> str:
        """Helper to map country to timezone"""
        timezone_map = {
            "US": "America/New_York",
            "CA": "America/Toronto",
            "MX": "America/Mexico_City",
            "GB": "Europe/London",
            "FR": "Europe/Paris",
            "DE": "Europe/Berlin",
        }
        return timezone_map.get(country, "UTC")
