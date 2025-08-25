"""
Conversation access plugin functions for advanced modules.

Provides access to conversation data, message history, and persona information
for use in advanced module scripts.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.script_plugins import plugin_registry
from app.models import Conversation, Message, Persona

logger = logging.getLogger(__name__)


class DictObject:
    """
    A wrapper that provides both dictionary and attribute access to data.
    
    Allows both persona_info.name and persona_info['name'] or persona_info.get('name') syntax.
    """
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize with dictionary data."""
        self._data = data
    
    def __getattr__(self, name: str) -> Any:
        """Provide attribute access to dictionary keys."""
        if name.startswith('_'):
            # Don't interfere with internal attributes
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __getitem__(self, key: str) -> Any:
        """Provide dictionary-style access."""
        return self._data[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Provide dict.get() method."""
        return self._data.get(key, default)
    
    def keys(self):
        """Provide dict.keys() method."""
        return self._data.keys()
    
    def values(self):
        """Provide dict.values() method."""
        return self._data.values()
    
    def items(self):
        """Provide dict.items() method."""
        return self._data.items()
    
    def __contains__(self, key: str) -> bool:
        """Provide 'in' operator support."""
        return key in self._data
    
    def __len__(self) -> int:
        """Provide len() support."""
        return len(self._data)
    
    def __str__(self) -> str:
        """String representation."""
        return str(self._data)
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"DictObject({self._data!r})"


@plugin_registry.register("get_message_count")
def get_message_count(conversation_id: Optional[str] = None, db_session: Session = None, _script_context: Any = None) -> int:
    """
    Get the total number of messages in a conversation.
    
    Args:
        conversation_id: ID of conversation to count messages for (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)
        
    Returns:
        Number of messages in the conversation
        
    Example:
        total_messages = ctx.get_message_count()
        other_conv_messages = ctx.get_message_count("other-conversation-id")
    """
    try:
        if db_session is None:
            logger.warning("get_message_count called without database session")
            return 0
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_message_count called without conversation_id and no script context")
                return 0
        
        # Check if conversation_id is still None (no conversation context available)
        if conversation_id is None:
            logger.debug("get_message_count called with None conversation_id - no conversation context available")
            return 0
        
        # Count messages in the specified conversation
        count = db_session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).count()
        
        logger.debug(f"Found {count} messages in conversation {conversation_id}")
        return count
        
    except Exception as e:
        logger.error(f"Error getting message count: {e}")
        return 0


@plugin_registry.register("get_raw_recent_messages")
def get_raw_recent_messages(
    limit: int = 10,
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> List[Dict[str, Any]]:
    """
    Get recent messages from a conversation as raw data dictionaries.
    
    Args:
        limit: Maximum number of messages to retrieve (default: 10)
        conversation_id: ID of conversation to get messages from (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        
    Returns:
        List of message dictionaries with role, content, and metadata
        
    Example:
        recent = ctx.get_raw_recent_messages(5)
        older_messages = ctx.get_raw_recent_messages(20, "other-conversation-id")
    """
    try:
        if db_session is None:
            logger.warning("get_raw_recent_messages called without database session")
            return []
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_raw_recent_messages called without conversation_id and no script context")
                return []
        
        # Get recent messages ordered by creation time (newest first)
        messages = db_session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        # Convert to dictionaries (reverse to get chronological order)
        result = []
        for message in reversed(messages):
            msg_dict = {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "thinking": message.thinking,
                "created_at": message.created_at.isoformat(),
                "input_tokens": message.input_tokens,
                "output_tokens": message.output_tokens,
                "preview": message.content[:100] + "..." if len(message.content) > 100 else message.content
            }
            result.append(msg_dict)
        
        logger.debug(f"Retrieved {len(result)} recent messages from conversation {conversation_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting recent messages: {e}")
        return []


@plugin_registry.register("get_recent_messages")
def get_recent_messages(
    limit: int = 5,
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> str:
    """
    Get recent messages from a conversation formatted for AI memory/context.
    
    Returns a nicely formatted string containing who said what and when,
    ready to be inserted directly into AI prompts for conversation memory.
    
    Args:
        limit: Maximum number of messages to retrieve (default: 5)
        conversation_id: ID of conversation to get messages from (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)
        
    Returns:
        Formatted string with recent conversation history for AI context
        
    Example:
        memory = ctx.get_recent_messages(3)
        # Returns:
        # "Recent conversation:
        # [2025-08-25 10:30] User: How do I create a new module?
        # [2025-08-25 10:31] Assistant: To create a new module, you can use the Modules section...
        # [2025-08-25 10:32] User: Thanks! What about advanced modules?"
    """
    try:
        if db_session is None:
            logger.warning("get_recent_messages called without database session")
            return "No conversation history available (no database session)"
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_recent_messages called without conversation_id and no script context")
                return "No conversation history available (no conversation context)"
        
        # Check if conversation_id is still None (no conversation context available)
        if conversation_id is None:
            logger.debug("get_recent_messages called with None conversation_id - no conversation context available")
            return "No conversation history available (no active conversation)"
        
        # Get recent messages ordered by creation time (newest first, then reverse for chronological order)
        messages = db_session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        if not messages:
            return "No conversation history available (no messages found)"
        
        # Format messages for AI memory
        formatted_lines = []
        
        # Reverse to get chronological order (oldest to newest)
        for message in reversed(messages):
            # Format timestamp
            try:
                timestamp = message.created_at.strftime("%H:%M")
            except:
                timestamp = "??:??"
            
            # Format role (User/Assistant/System)
            role = message.role.capitalize() if message.role else "Unknown"
            
            # Clean and truncate content for memory
            content = message.content.strip() if message.content else "[empty message]"
            
            # Truncate very long messages for memory efficiency
            if len(content) > 200:
                content = content[:197] + "..."
            
            # Replace newlines with spaces for single-line format
            content = content.replace('\n', ' ').replace('\r', ' ')
            
            # Format the message line
            formatted_lines.append(f"[{timestamp}] {role}: {content}")
        
        result = "\n".join(formatted_lines)
        
        logger.debug(f"Formatted {len(messages)} recent messages for conversation {conversation_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting formatted recent messages: {e}")
        return f"Error retrieving conversation history: {str(e)}"


@plugin_registry.register("get_conversation_summary")
def get_conversation_summary(conversation_id: Optional[str] = None, db_session: Session = None, _script_context: Any = None) -> Dict[str, Any]:
    """
    Get summary information about a conversation.
    
    Args:
        conversation_id: ID of conversation to summarize (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        
    Returns:
        Dictionary with conversation summary information
        
    Example:
        summary = ctx.get_conversation_summary()
        # Returns: {"message_count": 15, "title": "Chat", "created_at": "...", "personas": ["AVA"]}
    """
    try:
        if db_session is None:
            logger.warning("get_conversation_summary called without database session")
            return {}
            
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_conversation_summary called without conversation_id and no script context")
                return {}
        
        # Check if conversation_id is still None (no conversation context available)
        if conversation_id is None:
            logger.debug("get_conversation_summary called with None conversation_id - no conversation context available")
            return {"error": "No conversation context available", "message_count": 0}
        
        # Get conversation
        conversation = db_session.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return {}
        
        # Count messages
        message_count = db_session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).count()
        
        # Get persona info if available
        persona_name = "Unknown"
        if conversation.persona_id:
            persona = db_session.query(Persona).filter(
                Persona.id == conversation.persona_id
            ).first()
            if persona:
                persona_name = persona.name
        
        # Extract provider and model information
        provider = getattr(conversation, 'provider_type', None) or "unknown"
        model = "unknown"
        if hasattr(conversation, 'provider_config') and conversation.provider_config:
            # Extract model from provider_config JSON
            model = conversation.provider_config.get('model', 'unknown') if isinstance(conversation.provider_config, dict) else "unknown"
        
        # Build summary
        summary = {
            "id": str(conversation.id),
            "title": conversation.title,
            "message_count": message_count,
            "persona_name": persona_name,
            "persona_id": str(conversation.persona_id) if conversation.persona_id else None,
            "provider": provider,
            "model": model,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }
        
        logger.debug(f"Generated summary for conversation {conversation_id}: {message_count} messages")
        return summary
        
    except Exception as e:
        logger.error(f"Error getting conversation summary: {e}")
        return {}


@plugin_registry.register("get_persona_info")
def get_persona_info(persona_id: Optional[str] = None, db_session: Session = None, _script_context: Any = None) -> DictObject:
    """
    Get information about a persona.
    
    Args:
        persona_id: ID of persona to get info for (optional, uses current persona if not provided)
        db_session: Database session (auto-injected)
        
    Returns:
        DictObject with persona information supporting both attribute and dictionary access
        
    Example:
        persona = ctx.get_persona_info()
        # Both work:
        name = persona.name           # Attribute access
        name = persona['name']        # Dictionary access  
        name = persona.get('name')    # Dict.get() method
    """
    try:
        if db_session is None:
            logger.warning("get_persona_info called without database session")
            return DictObject({})
            
        if persona_id is None:
            if _script_context and hasattr(_script_context, 'persona_id'):
                persona_id = _script_context.persona_id
            else:
                logger.warning("get_persona_info called without persona_id and no script context")
                return DictObject({})
        
        # Get persona
        persona = db_session.query(Persona).filter(
            Persona.id == persona_id
        ).first()
        
        if not persona:
            logger.warning(f"Persona {persona_id} not found")
            return DictObject({})
        
        # Build persona info
        persona_info = {
            "id": str(persona.id),
            "name": persona.name,
            "description": persona.description,
            "template": persona.template,
            "is_active": persona.is_active,
            "created_at": persona.created_at.isoformat(),
            "updated_at": persona.updated_at.isoformat()
        }
        
        logger.debug(f"Retrieved info for persona {persona.name}")
        return DictObject(persona_info)
        
    except Exception as e:
        logger.error(f"Error getting persona info: {e}")
        return DictObject({})


@plugin_registry.register("get_conversation_history")
def get_conversation_history(
    conversation_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_session: Session = None,
    _script_context: Any = None
) -> List[Dict[str, Any]]:
    """
    Get conversation message history with pagination.
    
    Args:
        conversation_id: ID of conversation to get history for
        limit: Maximum number of messages to retrieve (default: 50)
        offset: Number of messages to skip (default: 0)
        db_session: Database session (auto-injected)
        
    Returns:
        List of message dictionaries in chronological order
        
    Example:
        history = ctx.get_conversation_history("conv-id", limit=20)
        older = ctx.get_conversation_history("conv-id", limit=20, offset=20)
    """
    try:
        if db_session is None:
            logger.warning("get_conversation_summary called without database session")
            return {}
            
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_conversation_summary called without conversation_id and no script context")
                return {}
        
        # Check if conversation_id is still None (no conversation context available)
        if conversation_id is None:
            logger.debug("get_conversation_summary called with None conversation_id - no conversation context available")
            return {"error": "No conversation context available", "message_count": 0}
        
        
        # Get messages with pagination, ordered chronologically
        messages = db_session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).offset(offset).limit(limit).all()
        
        # Convert to dictionaries
        result = []
        for message in messages:
            msg_dict = {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "thinking": message.thinking,
                "created_at": message.created_at.isoformat(),
                "input_tokens": message.input_tokens,
                "output_tokens": message.output_tokens
            }
            result.append(msg_dict)
        
        logger.debug(f"Retrieved {len(result)} messages from conversation {conversation_id} (offset={offset})")
        return result
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return []