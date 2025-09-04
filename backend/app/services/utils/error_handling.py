"""
Standardized error handling for HTTP operations and provider interactions.
"""

import logging
from typing import Callable, Any
from functools import wraps

from aiohttp import ClientConnectorError, ClientError, ClientResponseError
from ..exceptions import ProviderConnectionError, ProviderAuthenticationError

logger = logging.getLogger(__name__)


class HTTPErrorHandler:
    """Standardized error handling for HTTP operations."""
    
    @staticmethod
    def handle_http_errors(provider_name: str, url: str = None):
        """
        Decorator for standardized HTTP error handling across all providers.
        
        Args:
            provider_name: Name of the provider for error messages
            url: Optional URL for more specific error context
            
        Returns:
            Decorator function that handles HTTP errors consistently
        """
        def decorator(func: Callable) -> Callable:
            import inspect
            
            if inspect.isasyncgenfunction(func):
                # For async generators, create async generator wrapper
                @wraps(func)
                async def async_gen_wrapper(*args, **kwargs):
                    try:
                        async for item in func(*args, **kwargs):
                            yield item
                    except ClientConnectorError as e:
                        error_msg = f"Failed to connect to {provider_name}"
                        if url:
                            error_msg += f" at {url}"
                        error_msg += f": {str(e)}"
                        logger.error(error_msg)
                        raise ProviderConnectionError(error_msg)
                        
                    except ClientResponseError as e:
                        if e.status == 401:
                            error_msg = f"{provider_name} authentication failed: {e.message}"
                            logger.error(error_msg)
                            raise ProviderAuthenticationError(error_msg)
                        else:
                            error_msg = f"{provider_name} request failed with status {e.status}: {e.message}"
                            logger.error(error_msg)
                            raise ProviderConnectionError(error_msg)
                            
                    except ClientError as e:
                        error_msg = f"{provider_name} client error: {str(e)}"
                        logger.error(error_msg)
                        raise ProviderConnectionError(error_msg)
                        
                    except (ProviderAuthenticationError, ProviderConnectionError):
                        raise  # Re-raise provider errors without modification
                        
                    except Exception as e:
                        error_msg = f"Unexpected error in {provider_name} operation: {str(e)}"
                        logger.error(error_msg)
                        raise ProviderConnectionError(error_msg)
                
                return async_gen_wrapper
            else:
                # For regular async functions, create regular async wrapper
                @wraps(func)
                async def async_wrapper(*args, **kwargs) -> Any:
                    try:
                        return await func(*args, **kwargs)
                    except ClientConnectorError as e:
                        error_msg = f"Failed to connect to {provider_name}"
                        if url:
                            error_msg += f" at {url}"
                        error_msg += f": {str(e)}"
                        logger.error(error_msg)
                        raise ProviderConnectionError(error_msg)
                        
                    except ClientResponseError as e:
                        if e.status == 401:
                            error_msg = f"{provider_name} authentication failed: {e.message}"
                            logger.error(error_msg)
                            raise ProviderAuthenticationError(error_msg)
                        else:
                            error_msg = f"{provider_name} request failed with status {e.status}: {e.message}"
                            logger.error(error_msg)
                            raise ProviderConnectionError(error_msg)
                            
                    except ClientError as e:
                        error_msg = f"{provider_name} client error: {str(e)}"
                        logger.error(error_msg)
                        raise ProviderConnectionError(error_msg)
                        
                    except ProviderAuthenticationError:
                        raise  # Re-raise auth errors without modification
                        
                    except ProviderConnectionError:
                        raise  # Re-raise connection errors without modification
                        
                    except Exception as e:
                        error_msg = f"Unexpected error in {provider_name} operation: {str(e)}"
                        logger.error(error_msg)
                        raise ProviderConnectionError(error_msg)
                
                return async_wrapper
        return decorator
    
    @staticmethod
    async def check_response_status(response, provider_name: str) -> None:
        """
        Check HTTP response status and raise appropriate errors.
        
        Args:
            response: aiohttp ClientResponse object
            provider_name: Name of the provider for error messages
            
        Raises:
            ProviderAuthenticationError: For 401 status codes
            ProviderConnectionError: For other error status codes
        """
        if response.status == 401:
            try:
                error_text = await response.text()
            except Exception:
                error_text = "Authentication failed"
            raise ProviderAuthenticationError(f"{provider_name} authentication failed: {error_text}")
            
        elif response.status != 200:
            try:
                error_text = await response.text()
            except Exception:
                error_text = f"HTTP {response.status}"
            raise ProviderConnectionError(f"{provider_name} request failed with status {response.status}: {error_text}")