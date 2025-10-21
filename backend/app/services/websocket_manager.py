"""
WebSocket Connection Manager for chat sessions.

Manages active WebSocket connections and provides methods for sending
messages to specific sessions.
"""

import asyncio
import logging
from typing import Dict, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages active WebSocket connections for chat sessions.

    Provides thread-safe connection management and message broadcasting
    to specific sessions.
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        logger.info("WebSocketManager initialized")

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """
        Accept and register a WebSocket connection.

        Args:
            session_id: Unique session identifier
            websocket: WebSocket connection to register
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id} (total: {len(self.active_connections)})")

    async def disconnect(self, session_id: str) -> None:
        """
        Remove WebSocket connection.

        Args:
            session_id: Session ID to disconnect
        """
        async with self._lock:
            removed = self.active_connections.pop(session_id, None)

        if removed:
            logger.info(f"WebSocket disconnected: {session_id} (remaining: {len(self.active_connections)})")
        else:
            logger.warning(f"Attempted to disconnect non-existent session: {session_id}")

    def is_connected(self, session_id: str) -> bool:
        """
        Check if a session is currently connected.

        Args:
            session_id: Session ID to check

        Returns:
            True if session has active WebSocket connection
        """
        return session_id in self.active_connections

    async def send_message(self, session_id: str, message: dict) -> bool:
        """
        Send JSON message to specific session.

        Args:
            session_id: Target session ID
            message: Dictionary to send as JSON

        Returns:
            True if message sent successfully, False if session not found
        """
        websocket = self.active_connections.get(session_id)
        if not websocket:
            logger.warning(f"Cannot send message - session {session_id} not connected")
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to {session_id}: {e}")
            # Connection might be broken, remove it
            await self.disconnect(session_id)
            return False

    async def broadcast_chunk(self, session_id: str, chunk_type: str, data: dict) -> bool:
        """
        Send a chat chunk to the session with standardized format.

        Args:
            session_id: Target session ID
            chunk_type: Type of chunk (chunk, stage_update, done, error, etc.)
            data: Chunk data payload

        Returns:
            True if sent successfully
        """
        logger.debug(f"📤 Broadcasting {chunk_type} to {session_id}: {data}")
        result = await self.send_message(session_id, {
            "type": chunk_type,
            "data": data
        })
        if result:
            logger.debug(f"✅ Successfully sent {chunk_type} to {session_id}")
        else:
            logger.warning(f"❌ Failed to send {chunk_type} to {session_id}")
        return result

    async def get_active_session_count(self) -> int:
        """
        Get number of active WebSocket connections.

        Returns:
            Count of active connections
        """
        async with self._lock:
            return len(self.active_connections)

    async def get_active_session_ids(self) -> list[str]:
        """
        Get list of active session IDs.

        Returns:
            List of session IDs with active connections
        """
        async with self._lock:
            return list(self.active_connections.keys())


# Global WebSocket manager instance
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """
    Get or create the global WebSocket manager instance.

    Returns:
        WebSocketManager singleton instance
    """
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
