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
        
        # Count messages in the specified conversation
        count = db_session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).count()
        
        logger.debug(f"Found {count} messages in conversation {conversation_id}")
        return count
        
    except Exception as e:
        logger.error(f"Error getting message count: {e}")
        return 0


@plugin_registry.register("get_recent_messages")
def get_recent_messages(
    limit: int = 10,
    conversation_id: Optional[str] = None,
    db_session: Session = None,
    _script_context: Any = None
) -> List[Dict[str, Any]]:
    """
    Get recent messages from a conversation.
    
    Args:
        limit: Maximum number of messages to retrieve (default: 10)
        conversation_id: ID of conversation to get messages from (optional, uses current conversation if not provided)
        db_session: Database session (auto-injected)
        
    Returns:
        List of message dictionaries with role, content, and metadata
        
    Example:
        recent = ctx.get_recent_messages(5)
        older_messages = ctx.get_recent_messages(20, "other-conversation-id")
    """
    try:
        if db_session is None:
            logger.warning("get_recent_messages called without database session")
            return []
            
        # Use current conversation if none specified
        if conversation_id is None:
            if _script_context and hasattr(_script_context, 'conversation_id'):
                conversation_id = _script_context.conversation_id
            else:
                logger.warning("get_recent_messages called without conversation_id and no script context")
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
        
        # Build summary
        summary = {
            "id": str(conversation.id),
            "title": conversation.title,
            "message_count": message_count,
            "persona_name": persona_name,
            "persona_id": str(conversation.persona_id) if conversation.persona_id else None,
            "provider": conversation.provider,
            "model": conversation.model,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }
        
        logger.debug(f"Generated summary for conversation {conversation_id}: {message_count} messages")
        return summary
        
    except Exception as e:
        logger.error(f"Error getting conversation summary: {e}")
        return {}


@plugin_registry.register("get_persona_info")
def get_persona_info(persona_id: Optional[str] = None, db_session: Session = None, _script_context: Any = None) -> Dict[str, Any]:
    """
    Get information about a persona.
    
    Args:
        persona_id: ID of persona to get info for (optional, uses current persona if not provided)
        db_session: Database session (auto-injected)
        
    Returns:
        Dictionary with persona information
        
    Example:
        persona = ctx.get_persona_info()
        # Returns: {"name": "AVA", "description": "...", "template": "..."}
    """
    try:
        if db_session is None:
            logger.warning("get_persona_info called without database session")
            return {}
            
        if persona_id is None:
            if _script_context and hasattr(_script_context, 'persona_id'):
                persona_id = _script_context.persona_id
            else:
                logger.warning("get_persona_info called without persona_id and no script context")
                return {}
        
        # Get persona
        persona = db_session.query(Persona).filter(
            Persona.id == persona_id
        ).first()
        
        if not persona:
            logger.warning(f"Persona {persona_id} not found")
            return {}
        
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
        return persona_info
        
    except Exception as e:
        logger.error(f"Error getting persona info: {e}")
        return {}


@plugin_registry.register("get_conversation_history")
def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    db_session: Session = None
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
            logger.warning("get_conversation_history called without database session")
            return []
        
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