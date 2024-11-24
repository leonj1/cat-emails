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
        if not endpoint.startswith('/'):
            raise ValueError("API endpoint must start with '/'")

        if not self.api_token:
            raise ValueError("API token is required but not provided")
            
        if self.mock_mode:
            # Return empty lists in mock mode
            return []

        try:
            headers = {
                'Accept': 'application/json',
                'X-API-Token': f'{self.api_token}'
            }
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                timeout=10,
                headers=headers
            )
            response_data = response.json()
            print(f"RESPONSE: {response_data}")
            response.raise_for_status()

            if not isinstance(response_data, dict):
                raise ValueError("Expected dictionary response from API")
                
            # Handle allowed domains which come in 'domains' field
            if 'domains' in response_data:
                return [model_class(domain=d, is_active=True) for d in response_data['domains']]
            
            # Handle blocked domains/categories which may come in 'data' field
            if 'data' in response_data:
                domains_data = response_data['data']
                if not isinstance(domains_data, list):
                    raise ValueError("Expected array in 'data' field")
                return [model_class(**domain) for domain in domains_data]
                
            raise ValueError("Expected 'domains' or 'data' field in response")

        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch domains: {str(e)}") from e
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
            print(f"- {category.name} ({category.severity})")
            print(f"  Description: {category.description}")
    except Exception as e:
        print(f"Error: {str(e)}")
