"""
Async utilities for HTTP operations and session management.
"""

import asyncio
from typing import Optional
from aiohttp import ClientTimeout


class AsyncHTTPUtils:
    """Utilities for async HTTP operations."""
    
    @staticmethod
    def create_timeout(total_seconds: int = 300, connect_seconds: int = 30) -> ClientTimeout:
        """
        Create standardized HTTP timeout configuration.
        
        Args:
            total_seconds: Total timeout for the entire request
            connect_seconds: Connection timeout
            
        Returns:
            ClientTimeout configuration
        """
        return ClientTimeout(total=total_seconds, connect=connect_seconds)
    
    @staticmethod
    async def check_cancellation(session_id: Optional[str] = None) -> None:
        """
        Check for asyncio cancellation and handle gracefully.
        
        Args:
            session_id: Optional session ID for logging context
            
        Raises:
            asyncio.CancelledError: If the current task has been cancelled
        """
        try:
            current_task = asyncio.current_task()
            if current_task and current_task.cancelled():
                context = f"for session: {session_id}" if session_id else ""
                raise asyncio.CancelledError(f"Request cancelled {context}")
        except RuntimeError:
            pass
    
    @staticmethod
    def create_cancellation_token() -> asyncio.Event:
        """
        Create a cancellation token that can be used to signal cancellation.
        
        Returns:
            asyncio.Event that can be set to signal cancellation
        """
        return asyncio.Event()
    
    @staticmethod
    async def with_cancellation_check(coro, session_id: Optional[str] = None):
        """
        Execute a coroutine with cancellation checking.
        
        Args:
            coro: Coroutine to execute
            session_id: Optional session ID for context
            
        Returns:
            Result of the coroutine
            
        Raises:
            asyncio.CancelledError: If cancelled during execution
        """
        await AsyncHTTPUtils.check_cancellation(session_id)
        try:
            return await coro
        except asyncio.CancelledError:
            await AsyncHTTPUtils.check_cancellation(session_id)
            raise