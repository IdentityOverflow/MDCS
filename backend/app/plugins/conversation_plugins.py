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
        
        # Validate conversation_id is a proper UUID format
        try:
            import uuid
            uuid.UUID(str(conversation_id))
        except (ValueError, TypeError):
            # Invalid UUID format - likely a test scenario
            logger.debug(f"Invalid conversation_id format for message count: {conversation_id}")
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


@plugin_registry.register("get_message_range")
def get_message_range(
    start: int = 0,
    end: Optional[int] = None,
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> str:
    """
    Get a range of messages from a conversation formatted for AI context.

    Returns formatted messages from index `start` to `end` (exclusive).
    Similar to get_recent_messages() but for specific ranges.

    Args:
        start: Starting message index (0-based, inclusive)
        end: Ending message index (0-based, exclusive). If None, gets all messages from start onward.
        conversation_id: ID of conversation (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)

    Returns:
        Formatted string with message range for AI context

    Example:
        # Get messages 0-49 (first 50 messages)
        context = ctx.get_message_range(0, 50)

        # Get messages 20-39 (20 messages starting from index 20)
        context = ctx.get_message_range(20, 40)

        # Get all messages from index 100 onward
        context = ctx.get_message_range(100)
    """
    try:
        if db_session is None:
            logger.warning("get_message_range called without database session")
            return "No conversation history available (no database session)"

        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_message_range called without conversation_id and no script context")
                return "No conversation history available (no conversation context)"

        if conversation_id is None:
            logger.debug("get_message_range called with None conversation_id")
            return "No conversation history available (no active conversation)"

        # Calculate limit and offset
        offset = start
        if end is not None:
            limit = end - start
            if limit <= 0:
                return "No messages in range (end must be greater than start)"
        else:
            # Get a large number if no end specified
            limit = 10000

        # Get messages in chronological order
        messages = db_session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).offset(offset).limit(limit).all()

        if not messages:
            return f"No messages found in range {start} to {end if end else 'end'}"

        # Debug logging
        logger.info(f"get_message_range({start}, {end}): fetched {len(messages)} messages, first={messages[0].content[:50] if messages else 'none'}, last={messages[-1].content[:50] if messages else 'none'}")

        # Format messages for AI context (same format as get_recent_messages)
        formatted_lines = []

        for message in messages:
            # Format timestamp
            try:
                timestamp = message.created_at.strftime("%H:%M")
            except:
                timestamp = "??:??"

            # Format role
            role = message.role.capitalize() if message.role else "Unknown"

            # Get content without truncation
            content = message.content.strip() if message.content else "[empty message]"

            # Replace newlines with spaces for single-line format
            content = content.replace('\n', ' ').replace('\r', ' ')

            # Format the message line
            formatted_lines.append(f"[{timestamp}] {role}: {content}")

        result = "\n".join(formatted_lines)

        logger.debug(f"Formatted {len(messages)} messages from range {start}-{end if end else 'end'} for conversation {conversation_id}")
        return result

    except Exception as e:
        logger.error(f"Error getting message range: {e}")
        return f"Error retrieving message range: {str(e)}"


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


@plugin_registry.register("get_buffer_messages")
def get_buffer_messages(
    start_index: int = 25,
    end_index: int = 35,
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> List[Dict[str, Any]]:
    """
    Get messages from the memory buffer window for compression.
    
    Retrieves messages from a fixed buffer window (default: 25-35) that
    overlaps with short-term memory to provide compression context.
    
    Args:
        start_index: Starting message index (0-based, default: 25)
        end_index: Ending message index (0-based, default: 35)
        conversation_id: ID of conversation (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)
        
    Returns:
        List of message dictionaries in chronological order (oldest to newest)
        
    Example:
        buffer_msgs = ctx.get_buffer_messages(25, 35)  # Messages 25-35
        custom_buffer = ctx.get_buffer_messages(20, 30, "other-conv-id")
    """
    try:
        if db_session is None:
            logger.warning("get_buffer_messages called without database session")
            return []
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_buffer_messages called without conversation_id and no script context")
                return []
        
        # Check if conversation_id is still None
        if conversation_id is None:
            logger.debug("get_buffer_messages called with None conversation_id - no conversation context available")
            return []
        
        # Get messages in the specified range ordered chronologically
        messages = db_session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).offset(start_index).limit(end_index - start_index + 1).all()
        
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
        
        logger.debug(f"Retrieved {len(result)} buffer messages from conversation {conversation_id} (range {start_index}-{end_index})")
        return result
        
    except Exception as e:
        logger.error(f"Error getting buffer messages: {e}")
        return []


@plugin_registry.register("should_compress_buffer")
def should_compress_buffer(
    buffer_size: int = 11,
    min_total_messages: Optional[int] = None,
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> bool:
    """
    Check if the memory buffer should be compressed based on message count and compression history.
    
    Determines if there are enough messages in the buffer window and if compression
    hasn't already been performed at the current conversation size.
    
    Args:
        buffer_size: Required number of messages in buffer to trigger compression (default: 11)
        min_total_messages: Minimum total messages required (auto-calculated from buffer if not provided)
        conversation_id: ID of conversation (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)
        
    Returns:
        True if buffer should be compressed, False otherwise
        
    Example:
        if ctx.should_compress_buffer(buffer_size=6, min_total_messages=11):
            # Perform compression logic for messages 5-10
            pass
    """
    try:
        from ..models import ConversationMemory
        
        if db_session is None:
            logger.warning("should_compress_buffer called without database session")
            return False
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("should_compress_buffer called without conversation_id and no script context")
                return False
        
        # Check if conversation_id is still None
        if conversation_id is None:
            logger.debug("should_compress_buffer called with None conversation_id - no conversation context available")
            return False
        
        # Get total message count
        try:
            # Validate conversation_id is a proper UUID format
            import uuid
            uuid.UUID(str(conversation_id))
            
            total_messages = db_session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).count()
        except (ValueError, TypeError):
            # Invalid UUID format - likely a test scenario
            logger.debug(f"Invalid conversation_id format for compression check: {conversation_id}")
            return False
        
        # Auto-calculate minimum messages if not provided
        if min_total_messages is None:
            # For a buffer starting at index N with size S, we need N + S total messages
            # Default assumption: buffer starts after first few messages, so buffer_size + some offset
            min_total_messages = buffer_size + 5  # Rough heuristic
        
        # Use ConversationMemory model method to check if compression should occur
        should_compress = ConversationMemory.should_compress_now(
            db_session, 
            conversation_id, 
            total_messages,
            min_messages_required=min_total_messages
        )
        
        logger.debug(f"Buffer compression check for conversation {conversation_id}: "
                    f"total_messages={total_messages}, min_required={min_total_messages}, should_compress={should_compress}")
        
        return should_compress
        
    except Exception as e:
        logger.error(f"Error checking if buffer should be compressed: {e}")
        return False


@plugin_registry.register("should_compress_buffer_by_ids")
def should_compress_buffer_by_ids(
    buffer_message_ids: List[str],
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> bool:
    """
    Check if buffer should be compressed based on message IDs (prevents duplicate compression).
    
    This is more accurate than message counts because it checks if we've already
    compressed the exact same message range.
    
    Args:
        buffer_message_ids: List of message IDs in the current buffer
        conversation_id: ID of conversation (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)
        
    Returns:
        True if buffer should be compressed (no overlap with existing memories), False otherwise
        
    Example:
        buffer_msgs = ctx.get_buffer_messages(5, 10)
        msg_ids = [msg['id'] for msg in buffer_msgs]
        should_compress = ctx.should_compress_buffer_by_ids(msg_ids)
    """
    try:
        from ..models import ConversationMemory
        
        if db_session is None:
            logger.warning("should_compress_buffer_by_ids called without database session")
            return False
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("should_compress_buffer_by_ids called without conversation_id and no script context")
                return False
        
        # Check if conversation_id is still None
        if conversation_id is None:
            logger.debug("should_compress_buffer_by_ids called with None conversation_id - no conversation context available")
            return False
        
        # Validate conversation_id is a proper UUID format
        try:
            import uuid
            uuid.UUID(str(conversation_id))
        except (ValueError, TypeError):
            # Invalid UUID format - likely a test scenario
            logger.debug(f"Invalid conversation_id format for compression check: {conversation_id}")
            return False
        
        # Check if any of these messages have been compressed before
        has_overlap = ConversationMemory.has_compressed_message_range(
            db_session, 
            conversation_id, 
            buffer_message_ids
        )
        
        # Should compress only if there's NO overlap with existing memories
        should_compress = not has_overlap
        
        logger.debug(f"Message ID compression check for conversation {conversation_id}: "
                    f"buffer_size={len(buffer_message_ids)}, has_overlap={has_overlap}, should_compress={should_compress}")
        
        return should_compress
        
    except Exception as e:
        logger.error(f"Error checking message ID-based compression: {e}")
        return False


@plugin_registry.register("store_memory")
def store_memory(
    compressed_content: str,
    message_range: str = "25-35",
    total_messages: Optional[int] = None,
    first_message_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> Dict[str, Any]:
    """
    Store a compressed memory in the database.
    
    Saves an AI-generated memory summary to the conversation_memories table
    with automatic sequence numbering.
    
    Args:
        compressed_content: AI-generated memory summary text
        message_range: Range of messages that were compressed (default: "25-35")
        total_messages: Total message count when compression occurred (auto-calculated if not provided)
        first_message_id: ID of first message in compressed range (for overlap detection)
        conversation_id: ID of conversation (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)
        
    Returns:
        Dictionary with memory information or error details
        
    Example:
        memory_info = ctx.store_memory("User discussed project timeline and agreed on milestones", "25-35", 45)
    """
    try:
        from ..models import ConversationMemory
        
        if db_session is None:
            logger.warning("store_memory called without database session")
            return {"error": "No database session available"}
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("store_memory called without conversation_id and no script context")
                return {"error": "No conversation context available"}
        
        # Check if conversation_id is still None
        if conversation_id is None:
            logger.debug("store_memory called with None conversation_id - no conversation context available")
            return {"error": "No conversation context available"}
        
        # Validate compressed content
        if not compressed_content or not compressed_content.strip():
            logger.error("store_memory called with empty compressed_content")
            return {"error": "Compressed content cannot be empty"}
        
        # Get total message count if not provided
        if total_messages is None:
            total_messages = db_session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).count()
        
        # Store the compressed memory using model method
        memory = ConversationMemory.store_compressed_memory(
            db_session=db_session,
            conversation_id=conversation_id,
            compressed_content=compressed_content.strip(),
            message_range=message_range,
            total_messages=total_messages,
            first_message_id=first_message_id
        )
        
        # Commit the transaction
        db_session.commit()
        
        logger.debug(f"Stored compressed memory for conversation {conversation_id}: "
                    f"sequence={memory.memory_sequence}, range={message_range}")
        
        return {
            "success": True,
            "memory_id": str(memory.id),
            "memory_sequence": memory.memory_sequence,
            "message_range": message_range,
            "total_messages": total_messages
        }
        
    except Exception as e:
        logger.error(f"Error storing compressed memory: {e}")
        # Rollback the transaction on error
        if db_session:
            db_session.rollback()
        return {"error": f"Failed to store memory: {str(e)}"}


@plugin_registry.register("get_recent_memories") 
def get_recent_memories(
    limit: int = 10,
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> List[Dict[str, Any]]:
    """
    Get the most recent compressed memories for a conversation.
    
    Retrieves the last N compressed memories in reverse chronological order
    (most recent first) for insertion into persona templates.
    
    Args:
        limit: Maximum number of memories to retrieve (default: 10)
        conversation_id: ID of conversation (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)
        
    Returns:
        List of memory dictionaries (most recent first)
        
    Example:
        memories = ctx.get_recent_memories(5)  # Last 5 memories
        all_memories = ctx.get_recent_memories(100, "other-conv-id")  # Up to 100 memories
    """
    try:
        from ..models import ConversationMemory
        
        if db_session is None:
            logger.warning("get_recent_memories called without database session")
            return []
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_recent_memories called without conversation_id and no script context")
                return []
        
        # Check if conversation_id is still None
        if conversation_id is None:
            logger.debug("get_recent_memories called with None conversation_id - no conversation context available")
            return []
        
        # Validate conversation_id is a proper UUID format
        try:
            import uuid
            uuid.UUID(str(conversation_id))
        except (ValueError, TypeError):
            # Invalid UUID format - likely a test scenario
            logger.debug(f"Invalid conversation_id format for get_recent_memories: {conversation_id}")
            return []
        
        # Get recent memories using model method
        memories = ConversationMemory.get_recent_memories(
            db_session=db_session,
            conversation_id=conversation_id,
            limit=limit
        )
        
        # Convert to dictionaries
        result = [memory.to_dict() for memory in memories]
        
        logger.debug(f"Retrieved {len(result)} recent memories for conversation {conversation_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting recent memories: {e}")
        return []


@plugin_registry.register("get_memory_status")
def get_memory_status(
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> Dict[str, Any]:
    """
    Get comprehensive memory status for a conversation.
    
    Provides statistics and status information about both messages and memories
    for debugging and monitoring the memory factory system.
    
    Args:
        conversation_id: ID of conversation (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)
        
    Returns:
        Dictionary with memory status information
        
    Example:
        status = ctx.get_memory_status()
        # Returns: {"total_messages": 50, "total_memories": 3, "buffer_ready": True, ...}
    """
    try:
        from ..models import ConversationMemory
        
        if db_session is None:
            logger.warning("get_memory_status called without database session")
            return {"error": "No database session available"}
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_memory_status called without conversation_id and no script context")
                return {"error": "No conversation context available"}
        
        # Check if conversation_id is still None
        if conversation_id is None:
            logger.debug("get_memory_status called with None conversation_id - no conversation context available")
            return {"error": "No conversation context available"}
        
        # Get message count
        total_messages = db_session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).count()
        
        # Get memory count
        total_memories = db_session.query(ConversationMemory).filter(
            ConversationMemory.conversation_id == conversation_id
        ).count()
        
        # Check if buffer should be compressed
        buffer_ready = ConversationMemory.should_compress_now(
            db_session, conversation_id, total_messages
        )
        
        # Get latest memory sequence
        latest_memory = db_session.query(ConversationMemory.memory_sequence).filter(
            ConversationMemory.conversation_id == conversation_id
        ).order_by(ConversationMemory.memory_sequence.desc()).first()
        
        latest_sequence = latest_memory[0] if latest_memory else 0
        
        status = {
            "conversation_id": str(conversation_id),
            "total_messages": total_messages,
            "total_memories": total_memories,
            "latest_memory_sequence": latest_sequence,
            "buffer_ready_for_compression": buffer_ready,
            "buffer_window": "25-35",
            "buffer_size": 11,
            "has_sufficient_messages": total_messages >= 36
        }
        
        logger.debug(f"Memory status for conversation {conversation_id}: {status}")
        return status
        
    except Exception as e:
        logger.error(f"Error getting memory status: {e}")
        return {"error": f"Failed to get memory status: {str(e)}"}


@plugin_registry.register("clear_memories")
def clear_memories(
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> Dict[str, Any]:
    """
    Clear all memories for a conversation.
    
    Deletes all compressed memories from the database for the specified conversation.
    Use this to reset the memory system or for testing purposes.
    
    Args:
        conversation_id: ID of conversation (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        _script_context: Script execution context (auto-injected)
        
    Returns:
        Dictionary with number of memories cleared and status
        
    Example:
        result = ctx.clear_memories()
        # Returns: {"success": True, "deleted_count": 4, "conversation_id": "..."}
    """
    try:
        from ..models import ConversationMemory
        
        if db_session is None:
            logger.warning("clear_memories called without database session")
            return {"error": "No database session available"}
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("clear_memories called without conversation_id and no script context")
                return {"error": "No conversation context available"}
        
        # Check if conversation_id is still None
        if conversation_id is None:
            logger.debug("clear_memories called with None conversation_id - no conversation context available")
            return {"error": "No conversation context available"}
        
        # Validate conversation_id is a proper UUID format
        try:
            import uuid
            uuid.UUID(str(conversation_id))
        except (ValueError, TypeError):
            # Invalid UUID format - likely a test scenario
            logger.debug(f"Invalid conversation_id format for clear_memories: {conversation_id}")
            return {"error": f"Invalid conversation_id format: {conversation_id}"}
        
        # Clear all memories using model method
        deleted_count = ConversationMemory.clear_all_memories(
            db_session=db_session,
            conversation_id=conversation_id
        )
        
        # Commit the transaction
        db_session.commit()
        
        logger.info(f"Cleared {deleted_count} memories for conversation {conversation_id}")
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "conversation_id": str(conversation_id)
        }
        
    except Exception as e:
        logger.error(f"Error clearing memories: {e}")
        # Rollback the transaction on error
        if db_session:
            db_session.rollback()
        return {"error": f"Failed to clear memories: {str(e)}"}