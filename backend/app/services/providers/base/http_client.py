"""
Shared HTTP client functionality for all AI providers.

This module eliminates the duplicate HTTP handling code found across 
ollama_service_base.py and openai_service_base.py.
"""

import aiohttp
import logging
from typing import Dict, Any, Optional, AsyncIterator
from aiohttp import ClientSession, ClientTimeout

from ...utils.error_handling import HTTPErrorHandler
from ...utils.async_helpers import AsyncHTTPUtils

logger = logging.getLogger(__name__)


class BaseHTTPClient:
    """
    Shared HTTP client functionality for all providers.
    
    Eliminates ~200 lines of duplicate HTTP handling code across provider base classes.
    Provides standardized error handling, timeout management, and response processing.
    """
    
    def __init__(self, provider_name: str, default_timeout: int = 300):
        """
        Initialize HTTP client for a specific provider.
        
        Args:
            provider_name: Name of the provider (for logging and errors)
            default_timeout: Default timeout in seconds for requests
        """
        self.provider_name = provider_name
        self.default_timeout = default_timeout
    
    @HTTPErrorHandler.handle_http_errors("provider", "url")
    async def post_json(self, 
                       url: str, 
                       payload: Dict[str, Any], 
                       headers: Optional[Dict[str, str]] = None,
                       timeout: Optional[ClientTimeout] = None) -> Dict[str, Any]:
        """
        Execute JSON POST request with standardized error handling.
        
        Args:
            url: Target URL for the request
            payload: JSON payload to send
            headers: Optional HTTP headers
            timeout: Optional timeout configuration
            
        Returns:
            JSON response as dictionary
            
        Raises:
            ProviderConnectionError: For connection or HTTP errors
            ProviderAuthenticationError: For authentication failures
        """
        timeout = timeout or AsyncHTTPUtils.create_timeout(self.default_timeout)
        headers = headers or {}
        
        # Update decorator context for specific request
        decorator = HTTPErrorHandler.handle_http_errors(self.provider_name, url)
        
        @decorator
        async def _make_request():
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    await HTTPErrorHandler.check_response_status(response, self.provider_name)
                    return await response.json()
        
        return await _make_request()
    
    @HTTPErrorHandler.handle_http_errors("provider", "url")  
    async def stream_post(self, 
                         url: str, 
                         payload: Dict[str, Any],
                         headers: Optional[Dict[str, str]] = None,
                         timeout: Optional[ClientTimeout] = None) -> AsyncIterator[bytes]:
        """
        Execute streaming POST request with standardized error handling.
        
        Args:
            url: Target URL for the request
            payload: JSON payload to send
            headers: Optional HTTP headers
            timeout: Optional timeout configuration
            
        Yields:
            Raw bytes from the streaming response
            
        Raises:
            ProviderConnectionError: For connection or HTTP errors
            ProviderAuthenticationError: For authentication failures
        """
        timeout = timeout or AsyncHTTPUtils.create_timeout(self.default_timeout)
        headers = headers or {}
        
        # Update decorator context for specific request
        decorator = HTTPErrorHandler.handle_http_errors(self.provider_name, url)
        
        @decorator
        async def _make_stream_request():
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    await HTTPErrorHandler.check_response_status(response, self.provider_name)
                    async for chunk in response.content.iter_chunked(8192):
                        if chunk:
                            yield chunk
        
        async for chunk in _make_stream_request():
            yield chunk
    
    async def get_json(self, 
                      url: str, 
                      headers: Optional[Dict[str, str]] = None,
                      timeout: Optional[ClientTimeout] = None) -> Dict[str, Any]:
        """
        Execute JSON GET request with standardized error handling.
        
        Args:
            url: Target URL for the request
            headers: Optional HTTP headers
            timeout: Optional timeout configuration
            
        Returns:
            JSON response as dictionary
            
        Raises:
            ProviderConnectionError: For connection or HTTP errors
            ProviderAuthenticationError: For authentication failures
        """
        timeout = timeout or AsyncHTTPUtils.create_timeout(self.default_timeout)
        headers = headers or {}
        
        decorator = HTTPErrorHandler.handle_http_errors(self.provider_name, url)
        
        @decorator
        async def _make_request():
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    await HTTPErrorHandler.check_response_status(response, self.provider_name)
                    return await response.json()
        
        return await _make_request()