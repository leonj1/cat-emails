from typing import List, Type
from pydantic import BaseModel
import requests


class AllowedDomain(BaseModel):
    domain: str
    is_active: bool


class BlockedDomain(BaseModel):
    domain: str
    reason: str


class BlockedCategory(BaseModel):
    category: str
    reason: str


class DomainService:
    def __init__(self, base_url: str = "https://control-api.joseserver.com", api_token: str | None = None):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.mock_mode = api_token is None
        
    def fetch_allowed_domains(self) -> List[AllowedDomain]:
        return self._fetch("/domains/allowed", AllowedDomain)

    def fetch_blocked_domains(self) -> List[BlockedDomain]:
        return self._fetch("/domains/blocked", BlockedDomain)

    def fetch_blocked_categories(self) -> List[BlockedCategory]:
        try:
            return self._fetch("/categories/blocked", BlockedCategory)
        except Exception as e:
            # Fallback to default blocked categories if API fails
            print(f"Warning: Failed to fetch blocked categories from API: {e}")
            print("Using default blocked categories: Advertising, Marketing, Wants-Money")
            return [
                BlockedCategory(category="Advertising", reason="Default fallback category"),
                BlockedCategory(category="Marketing", reason="Default fallback category"),
                BlockedCategory(category="Wants-Money", reason="Default fallback category")
            ]

    def _fetch(self, endpoint: str, model_class: Type[BaseModel]) -> List[BaseModel]:
        if self.mock_mode:
            # Return default blocked categories in mock mode to enable email deletion
            if endpoint == "/categories/blocked":
                return [
                    BlockedCategory(category="Advertising", reason="Default blocked category"),
                    BlockedCategory(category="Marketing", reason="Default blocked category"),
                    BlockedCategory(category="Wants-Money", reason="Default blocked category")
                ]
            # Return empty lists for domains in mock mode
            return []
            
        if not self.api_token:
            raise ValueError("API token is required but not provided")

        try:
            headers = {
                'Accept': 'application/json',
                'X-API-Token': self.api_token
            }
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                timeout=10,
                headers=headers
            )
            response.raise_for_status()
            response_data = response.json()
            
            # Handle different response formats based on endpoint
            if endpoint == "/domains/allowed":
                if not isinstance(response_data, dict) or 'domains' not in response_data:
                    raise ValueError("Expected 'domains' field in response")
                return [model_class(domain=d, is_active=True) for d in response_data['domains']]
            
            elif endpoint == "/domains/blocked":
                if not isinstance(response_data, dict) or 'domains' not in response_data:
                    raise ValueError("Expected 'domains' field in response")
                return [model_class(domain=d, reason="Blocked by policy") for d in response_data['domains']]
            
            elif endpoint == "/categories/blocked":
                if not isinstance(response_data, dict) or 'categories' not in response_data:
                    raise ValueError("Expected 'categories' field in response")
                return [model_class(category=c, reason="Blocked by policy") for c in response_data['categories']]
            
            else:
                raise ValueError(f"Unsupported endpoint: {endpoint}")

        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch from API: {str(e)}") from e
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid response format from API: {str(e)}") from e

# Example usage:
if __name__ == "__main__":
    import os
    api_token = os.getenv("CONTROL_TOKEN")
    if not api_token:
        print("Error: CONTROL_TOKEN environment variable is not set")
        exit(1)
        
    service = DomainService(api_token=api_token)
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
            print(f"- {category.category} (Reason: {category.reason})")
    except Exception as e:
        print(f"Error: {str(e)}")
