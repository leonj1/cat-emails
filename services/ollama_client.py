"""
Resilient Ollama client with automatic failover support.
"""
import logging
import time
from typing import Optional, List, Dict, Any, Callable
from urllib.parse import urlparse
import requests
import openai
from openai import OpenAI

logger = logging.getLogger(__name__)


class OllamaHost:
    """Represents an Ollama host with health tracking."""
    
    def __init__(self, base_url: str, name: str = ""):
        self.base_url = base_url.rstrip('/')
        if not self.base_url.startswith('http'):
            self.base_url = f"http://{self.base_url}"
        self.name = name or base_url
        self.is_healthy = True
        self.last_check = 0
        self.consecutive_failures = 0
        self.client = OpenAI(
            base_url=f"{self.base_url}/v1",
            api_key="ollama"  # Required but not used by Ollama
        )
    
    def health_check(self) -> bool:
        """Check if the Ollama host is responsive."""
        try:
            # Try to list models as a health check
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self.is_healthy = True
                self.consecutive_failures = 0
                logger.debug(f"Health check passed for {self.name}")
                return True
        except Exception as e:
            logger.warning(f"Health check failed for {self.name}: {str(e)}")
        
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.is_healthy = False
        return False
    
    def __str__(self):
        return f"{self.name} ({'healthy' if self.is_healthy else 'unhealthy'})"


class ResilientOllamaClient:
    """
    A resilient Ollama client that automatically fails over between multiple hosts.
    """
    
    def __init__(self, 
                 primary_host: str,
                 secondary_host: Optional[str] = None,
                 health_check_interval: int = 300,  # 5 minutes
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize the resilient Ollama client.
        
        Args:
            primary_host: Primary Ollama host URL
            secondary_host: Secondary Ollama host URL (optional)
            health_check_interval: Seconds between health checks
            max_retries: Maximum retry attempts per host
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.hosts = [OllamaHost(primary_host, "primary")]
        if secondary_host:
            self.hosts.append(OllamaHost(secondary_host, "secondary"))
        
        self.health_check_interval = health_check_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.current_host_index = 0
        
        # Perform initial health checks
        logger.info(f"Initializing Ollama client with {len(self.hosts)} host(s)")
        self._perform_health_checks()
    
    def _perform_health_checks(self):
        """Perform health checks on all hosts."""
        current_time = time.time()
        
        for host in self.hosts:
            # Only check if enough time has passed since last check
            if current_time - host.last_check >= self.health_check_interval:
                host.health_check()
                host.last_check = current_time
    
    def _get_available_host(self) -> Optional[OllamaHost]:
        """Get the next available healthy host."""
        # First, try to find a healthy host starting from current index
        for i in range(len(self.hosts)):
            idx = (self.current_host_index + i) % len(self.hosts)
            host = self.hosts[idx]
            if host.is_healthy:
                self.current_host_index = idx
                return host
        
        # If no healthy hosts, try health checks again
        logger.warning("No healthy hosts available, performing emergency health checks")
        self._perform_health_checks()
        
        # Try one more time
        for host in self.hosts:
            if host.is_healthy:
                return host
        
        # Last resort: return the primary host
        logger.error("All hosts appear unhealthy, attempting with primary host")
        return self.hosts[0]
    
    def _execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic and automatic failover.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function call
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        hosts_tried = set()
        
        for attempt in range(self.max_retries * len(self.hosts)):
            # Perform periodic health checks
            self._perform_health_checks()
            
            # Get an available host
            host = self._get_available_host()
            if not host:
                raise Exception("No available Ollama hosts")
            
            hosts_tried.add(host.name)
            
            try:
                logger.debug(f"Attempting request with {host.name} (attempt {attempt + 1})")
                
                # Replace the client in kwargs with the current host's client
                kwargs_copy = kwargs.copy()
                if 'client' in kwargs_copy:
                    kwargs_copy['client'] = host.client
                
                result = func(*args, **kwargs_copy)
                
                # Reset failure count on success
                host.consecutive_failures = 0
                
                # Log if we had to failover
                if len(hosts_tried) > 1:
                    logger.info(f"Request succeeded after failover to {host.name}")
                
                return result
                
            except Exception as e:
                last_exception = e
                host.consecutive_failures += 1
                
                # Mark host as unhealthy if too many failures
                if host.consecutive_failures >= 3:
                    host.is_healthy = False
                    logger.warning(f"Marking {host.name} as unhealthy after {host.consecutive_failures} failures")
                
                # Log the error
                logger.warning(f"Request failed on {host.name}: {str(e)}")
                
                # Move to next host
                self.current_host_index = (self.current_host_index + 1) % len(self.hosts)
                
                # Exponential backoff
                if attempt < (self.max_retries * len(self.hosts) - 1):
                    delay = self.retry_delay * (2 ** (attempt % self.max_retries))
                    logger.debug(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
        
        # All attempts failed
        hosts_summary = ", ".join(hosts_tried)
        raise Exception(f"All retry attempts failed across hosts: {hosts_summary}. Last error: {str(last_exception)}")
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Any:
        """
        Create a chat completion with automatic failover.
        
        Args:
            model: The model to use
            messages: The chat messages
            **kwargs: Additional arguments for the completion
            
        Returns:
            The completion response
        """
        def _create_completion(client):
            return client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
        
        return self._execute_with_retry(_create_completion, client=None)
    
    def get_current_host(self) -> str:
        """Get the current active host."""
        if self.hosts:
            return self.hosts[self.current_host_index].name
        return "none"
    
    def get_hosts_status(self) -> Dict[str, bool]:
        """Get the health status of all hosts."""
        return {host.name: host.is_healthy for host in self.hosts}


def create_resilient_client(primary_host: Optional[str] = None,
                           secondary_host: Optional[str] = None) -> ResilientOllamaClient:
    """
    Create a resilient Ollama client with default configuration.
    
    Args:
        primary_host: Primary host URL (defaults to environment variable)
        secondary_host: Secondary host URL (defaults to environment variable)
        
    Returns:
        ResilientOllamaClient instance
    """
    import os
    
    if not primary_host:
        primary_host = os.environ.get('OLLAMA_HOST_PRIMARY', '10.1.1.247:11434')
    
    if not secondary_host:
        secondary_host = os.environ.get('OLLAMA_HOST_SECONDARY', '10.1.1.212:11434')
    
    return ResilientOllamaClient(
        primary_host=primary_host,
        secondary_host=secondary_host
    )