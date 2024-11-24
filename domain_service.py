import requests
from typing import List
from pydantic import BaseModel, Field

class AllowedDomain(BaseModel):
    domain: str = Field(description="The domain name")
    is_active: bool = Field(description="Whether the domain is active")

class BlockedDomain(BaseModel):
    domain: str = Field(description="The domain name")
    reason: str = Field(description="The reason for blocking this domain")

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
            response = requests.get(
                f"{self.base_url}/api/v1/domains/allowed",
                timeout=10,  # Add reasonable timeout
                headers={'Accept': 'application/json'}
            )
            response.raise_for_status()
            
            domains_data = response.json()
            if not isinstance(domains_data, list):
                raise ValueError("Expected array response from API")
                
            return [AllowedDomain(**domain) for domain in domains_data]
            
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch allowed domains: {str(e)}") from e
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid response format from API: {str(e)}") from e

    def fetch_blocked_domains(self) -> List[BlockedDomain]:
        """
        Fetch the list of blocked domains from the control API.
        
        Returns:
            List[BlockedDomain]: A list of blocked domains with their blocking reasons
            
        Raises:
            requests.RequestException: If there's an error communicating with the API
            ValueError: If the API response is not in the expected format
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/domains/blocked",
                timeout=10,
                headers={'Accept': 'application/json'}
            )
            response.raise_for_status()
            
            domains_data = response.json()
            if not isinstance(domains_data, list):
                raise ValueError("Expected array response from API")
                
            return [BlockedDomain(**domain) for domain in domains_data]
            
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch blocked domains: {str(e)}") from e
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
    except Exception as e:
        print(f"Error: {str(e)}")
