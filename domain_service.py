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
        return self._fetch("/categories/blocked", BlockedCategory)

    def _fetch(self, endpoint: str, model_class: Type[BaseModel]) -> List[BaseModel]:
        if not self.api_token:
            raise ValueError("API token is required but not provided")
            
        if self.mock_mode:
            # Return empty lists in mock mode
            return []

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
            
            # Handle allowed domains which come in 'domains' field
            if endpoint == "/domains/allowed":
                if not isinstance(response_data, dict) or 'domains' not in response_data:
                    raise ValueError("Expected 'domains' field in response")
                return [model_class(domain=d, is_active=True) for d in response_data['domains']]
            
            # Handle blocked domains/categories which come in 'data' field
            if not isinstance(response_data, dict) or 'data' not in response_data:
                raise ValueError("Expected 'data' field in response")
            
            data = response_data['data']
            if not isinstance(data, list):
                raise ValueError("Expected array in 'data' field")
                
            return [model_class(**item) for item in data]

        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch from API: {str(e)}") from e
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid response format from API: {str(e)}") from e

# Example usage:
if __name__ == "__main__":
    import os
    api_token = os.getenv("CONTROL_API_TOKEN")
    if not api_token:
        print("Error: CONTROL_API_TOKEN environment variable is not set")
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
