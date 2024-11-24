import requests
from typing import List, Type
from pydantic import BaseModel, Field

class AllowedDomain(BaseModel):
    domain: str = Field(description="The domain name")
    is_active: bool = Field(description="Whether the domain is active")

class BlockedDomain(BaseModel):
    domain: str = Field(description="The domain name")
    reason: str = Field(description="The reason for blocking this domain")

class BlockedCategory(BaseModel):
    name: str = Field(description="The category name")
    description: str = Field(description="Description of the category")
    severity: str = Field(description="Severity level of the category")

class DomainService:
    def __init__(self, base_url: str = "https://control-api.joseserver.com"):
        self.base_url = base_url.rstrip('/')
        
    def fetch_allowed_domains(self) -> List[AllowedDomain]:
        return self._fetch_domains("/api/v1/domains/allowed", AllowedDomain)

    def fetch_blocked_domains(self) -> List[BlockedDomain]:
        return self._fetch_domains("/api/v1/domains/blocked", BlockedDomain)

    def fetch_blocked_categories(self) -> List[BlockedCategory]:
        """
        Fetch the list of blocked categories from the control API.

        Returns:
            List[BlockedCategory]: A list of blocked categories

        Raises:
            requests.RequestException: If there's an error communicating with the API
            ValueError: If the API response is not in the expected format
        """
        return self._fetch_domains("/api/v1/categories/blocked", BlockedCategory)

    def _fetch_domains(self, endpoint: str, model_class: Type[BaseModel]) -> List[BaseModel]:
        """
        Generic method to fetch domains from the API.

        Args:
            endpoint: API endpoint path
            model_class: Pydantic model class to parse the response

        Returns:
            List of domain objects

        Raises:
            requests.RequestException: If there's an error communicating with the API
            ValueError: If the API response is not in the expected format
        """
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                timeout=10,
                headers={'Accept': 'application/json'}
            )
            response.raise_for_status()

            domains_data = response.json()
            if not isinstance(domains_data, list):
                raise ValueError("Expected array response from API")

            return [model_class(**domain) for domain in domains_data]

        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch domains: {str(e)}") from e
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid response format from API: {str(e)}") from e

# Example usage:
if __name__ == "__main__":
    service = DomainService()
    try:
        allowed_domains = service.fetch_allowed_domains()
        print("\nAllowed Domains:")
        for domain in allowed_domains:
            status = "active" if domain.is_active else "inactive"
            print(f"- {domain.domain} ({status})")

        blocked_domains = service.fetch_blocked_domains()
        print("\nBlocked Domains:")
        for domain in blocked_domains:
            print(f"- {domain.domain} (Reason: {domain.reason})")

        blocked_categories = service.fetch_blocked_categories()
        print("\nBlocked Categories:")
        for category in blocked_categories:
            print(f"- {category.name} ({category.severity})")
            print(f"  Description: {category.description}")
    except Exception as e:
        print(f"Error: {str(e)}")
