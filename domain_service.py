import requests
from typing import List
from pydantic import BaseModel

class AllowedDomain(BaseModel):
    domain: str
    is_active: bool

class DomainService:
    def __init__(self, base_url: str = "https://control-api.joseserver.com"):
        self.base_url = base_url.rstrip('/')
        
    def fetch_allowed_domains(self) -> List[AllowedDomain]:
        """
        Fetch the list of allowed domains from the control API.
        
        Returns:
            List[AllowedDomain]: A list of allowed domains with their active status
            
        Raises:
            requests.RequestException: If there's an error communicating with the API
            ValueError: If the API response is not in the expected format
        """
        try:
            response = requests.get(f"{self.base_url}/api/v1/domains/allowed")
            response.raise_for_status()
            
            domains_data = response.json()
            return [AllowedDomain(**domain) for domain in domains_data]
            
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch allowed domains: {str(e)}")
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid response format from API: {str(e)}")

# Example usage:
if __name__ == "__main__":
    service = DomainService()
    try:
        allowed_domains = service.fetch_allowed_domains()
        print("Allowed Domains:")
        for domain in allowed_domains:
            status = "active" if domain.is_active else "inactive"
            print(f"- {domain.domain} ({status})")
    except Exception as e:
        print(f"Error: {str(e)}")
