"""
Custom exceptions for AI provider services.
"""


class UnsupportedProviderError(Exception):
    """Raised when an unsupported provider type is requested."""
    
    def __init__(self, provider_type: str):
        self.provider_type = provider_type
        super().__init__(f"Unsupported provider type: {provider_type}")


class ProviderConnectionError(Exception):
    """Raised when a provider connection fails."""
    pass


class ProviderAuthenticationError(Exception):
    """Raised when provider authentication fails."""
    pass