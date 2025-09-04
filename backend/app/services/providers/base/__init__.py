"""
Base abstractions for AI provider implementations.
"""

from .http_client import BaseHTTPClient
from .stream_processor import BaseStreamProcessor
from .provider_service import BaseProviderService

__all__ = [
    'BaseHTTPClient',
    'BaseStreamProcessor',
    'BaseProviderService'
]