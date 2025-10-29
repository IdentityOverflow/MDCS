"""
WebSocket endpoint for real-time chat with bidirectional cancellation support.

This replaces the SSE (Server-Sent Events) implementation to enable immediate
cancellation of AI inference at any stage.
"""

import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..services.websocket_manager import get_websocket_manager, WebSocketManager
from ..services.chat_session_manager import get_chat_session_manager, ChatSessionManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
    session_manager: ChatSessionManager = Depends(get_chat_session_manager)
):
    """
    WebSocket endpoint for chat with real-time cancellation support.

    Message Types (Client → Server):
        - {"type": "chat", "message": "...", "provider": "ollama", "persona_id": "...", ...}
        - {"type": "cancel", "session_id": "..."}
        - {"type": "ping"}

    Message Types (Server → Client):
        - {"type": "session_start", "data": {"session_id": "..."}}
        - {"type": "stage_update", "data": {"stage": "...", "message": "..."}}
        - {"type": "chunk", "data": {"content": "...", "thinking": "...", "done": false}}
        - {"type": "done", "data": {"metadata": {...}}}
        - {"type": "cancelled", "data": {"message": "...", "session_id": "..."}}
        - {"type": "error", "data": {"error": "...", "session_id": "..."}}
        - {"type": "pong"}
    """

    # Generate session ID for this connection
    session_id = str(uuid.uuid4())

    try:
        # Accept and register WebSocket connection
        await ws_manager.connect(session_id, websocket)
        logger.info(f"✅ WebSocket connected: {session_id}")

        # Send session start message immediately
        await ws_manager.send_message(session_id, {
            "type": "session_start",
            "data": {"session_id": session_id}
        })

        # Message receive loop
        while True:
            try:
                # Wait for message from client
                message = await websocket.receive_json()
                message_type = message.get("type")

                # Route message based on type
                if message_type == "chat":
                    # Start chat handler in thread pool to prevent blocking the event loop
                    # This is CRITICAL: handle_chat_message uses sync DB queries which block
                    async def chat_task():
                        # Create a new database session for this task
                        from ..database.connection import db_manager
                        task_db = db_manager.get_session()
                        try:
                            # Run in thread pool executor to prevent blocking
                            import concurrent.futures
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(
                                None,  # Use default ThreadPoolExecutor
                                lambda: asyncio.run(handle_chat_message(
                                    message=message,
                                    session_id=session_id,
                                    db=task_db,
                                    ws_manager=ws_manager,
                                    session_manager=session_manager
                                ))
                            )
                            # Commit successful execution
                            task_db.commit()
                        except Exception as e:
                            # Rollback on any exception to prevent transaction state issues
                            task_db.rollback()
                            logger.error(f"Chat task failed for session {session_id}: {e}")
                            raise
                        finally:
                            task_db.close()

                    asyncio.create_task(chat_task())

                elif message_type == "cancel":
                    # Handle cancel request - get chat session ID from message
                    cancel_session_id = message.get("session_id")
                    if not cancel_session_id:
                        logger.warning(f"Cancel request missing session_id")
                        await ws_manager.broadcast_chunk(session_id, "error", {
                            "error": "Cancel request missing session_id",
                            "session_id": session_id
                        })
                        continue

                    await handle_cancel_request(
                        session_id=cancel_session_id,
                        ws_session_id=session_id,
                        session_manager=session_manager,
                        ws_manager=ws_manager
                    )

                elif message_type == "ping":
                    # Respond to ping with pong
                    await ws_manager.send_message(session_id, {"type": "pong"})

                else:
                    logger.warning(f"Unknown message type: {message_type}")

            except WebSocketDisconnect:
                # Client disconnected - break loop immediately
                logger.info(f"🔌 Client disconnected during message loop: {session_id}")
                break

            except RuntimeError as runtime_err:
                # Check if this is a disconnect-related error
                if "disconnect" in str(runtime_err).lower():
                    logger.info(f"🔌 Disconnect detected via RuntimeError: {session_id}")
                    break
                # Other runtime errors - log and break to avoid infinite loop
                logger.error(f"Runtime error for {session_id}: {runtime_err}")
                break

            except Exception as msg_error:
                # Check if error message indicates disconnect
                error_str = str(msg_error).lower()
                if "disconnect" in error_str or "closed" in error_str or "receive" in error_str:
                    logger.info(f"🔌 Disconnect detected via exception: {session_id}")
                    break

                # Other errors - log but don't send error message if connection is dead
                logger.error(f"Error processing message for {session_id}: {msg_error}")
                try:
                    await ws_manager.broadcast_chunk(session_id, "error", {
                        "error": f"Message processing error: {str(msg_error)}",
                        "session_id": session_id
                    })
                except:
                    # If we can't send error, connection is dead - break loop
                    logger.warning(f"Cannot send error message - connection dead for {session_id}")
                    break

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"❌ WebSocket error for {session_id}: {e}")
        try:
            await ws_manager.broadcast_chunk(session_id, "error", {
                "error": str(e),
                "session_id": session_id
            })
        except:
            pass  # Connection might be broken

    finally:
        # Clean up connection and session
        await ws_manager.disconnect(session_id)
        await session_manager.remove_session(session_id)
        logger.debug(f"🧹 Cleaned up session {session_id}")


async def handle_chat_message(
    message: dict,
    session_id: str,
    db: Session,
    ws_manager: WebSocketManager,
    session_manager: ChatSessionManager
):
    """
    Handle incoming chat message asynchronously.

    This is the main chat processing pipeline that will be implemented
    to replace the SSE streaming endpoint.

    Args:
        message: Chat message dict from client
        session_id: WebSocket session ID
        db: Database session
        ws_manager: WebSocket manager for sending responses
        session_manager: Chat session manager for cancellation
    """

    try:
        # Import dependencies at the start
        import asyncio
        import uuid
        from ..services.modules import StagedModuleResolver
        from ..services.ai_providers import ProviderType, ProviderFactory, ChatRequest
        from ..models import Persona
        from .chat_models import ProcessingStage
        from uuid import UUID

        # Generate a unique chat session ID for this message (separate from WebSocket connection ID)
        chat_session_id = str(uuid.uuid4())

        logger.info(f"💬 Processing chat message for WebSocket {session_id}, chat session {chat_session_id}")

        # Extract request data
        data = message.get("data", {})
        user_message = data.get("message")
        provider_str = data.get("provider", "ollama")
        persona_id = data.get("persona_id")
        conversation_id = data.get("conversation_id")
        provider_settings = data.get("provider_settings", {})
        chat_controls = data.get("chat_controls", {})

        if not user_message:
            await ws_manager.broadcast_chunk(session_id, "error", {
                "error": "No message provided",
                "session_id": session_id
            })
            return

        # Register chat session with cancellation token (use chat_session_id, not WebSocket session_id)
        try:
            cancellation_token = await session_manager.register_session(
                session_id=chat_session_id,
                conversation_id=conversation_id
            )
            logger.debug(f"✅ Registered chat session {chat_session_id}")
        except ValueError as e:
            logger.warning(f"Chat session {chat_session_id} registration failed: {e}")
            await ws_manager.broadcast_chunk(session_id, "error", {
                "error": f"Failed to register chat session: {str(e)}",
                "session_id": session_id
            })
            return

        # Send chat session ID to frontend for cancellation
        # CRITICAL: This must be sent AND received before any stage execution
        logger.info(f"🆔 Sending chat_session_start to frontend: chat_session_id={chat_session_id}, ws_session_id={session_id}")
        await ws_manager.broadcast_chunk(session_id, "chat_session_start", {
            "chat_session_id": chat_session_id
        })

        # Yield to event loop to ensure message is transmitted before stage execution
        await asyncio.sleep(0)
        logger.info(f"🆔 Sent chat_session_start message")

        # Stage 1: THINKING_BEFORE - Resolve system prompt (Stages 1-2)
        await ws_manager.broadcast_chunk(session_id, "stage_update", {
            "stage": ProcessingStage.THINKING_BEFORE.value,
            "message": "Resolving system prompt..."
        })

        # Resolve system prompt from persona
        resolved_system_prompt = ""
        if persona_id:
            try:
                # Fetch persona
                persona_uuid = UUID(persona_id)
                persona = db.query(Persona).filter(
                    Persona.id == persona_uuid,
                    Persona.is_active == True
                ).first()

                if not persona:
                    await ws_manager.broadcast_chunk(session_id, "error", {
                        "error": f"Persona {persona_id} not found or inactive",
                        "session_id": session_id
                    })
                    return

                # Initialize resolver with cancellation support (used for both template and POST_RESPONSE)
                resolver = StagedModuleResolver(db_session=db)
                resolver.enable_state_tracking()
                resolver.session_manager.set_cancellation_token(cancellation_token)

                if persona.template:

                    # Build trigger context
                    trigger_context = {"last_user_message": user_message}

                    # Resolve template using async Stages 1+2
                    result = await resolver.resolve_template_stages_1_and_2(
                        template=persona.template,
                        session_id=chat_session_id,  # Use chat session ID
                        conversation_id=conversation_id,
                        persona_id=persona_id,
                        db_session=db,
                        trigger_context=trigger_context,
                        current_provider=provider_str,
                        current_provider_settings=provider_settings,
                        current_chat_controls=chat_controls
                    )

                    resolved_system_prompt = result.resolved_template

                    # Log warnings
                    if result.warnings:
                        logger.warning(f"Template resolution warnings: {len(result.warnings)}")
                        for warning in result.warnings:
                            logger.warning(f"  {warning.warning_type}: {warning.message}")

            except Exception as persona_error:
                logger.error(f"Error resolving persona: {persona_error}")
                await ws_manager.broadcast_chunk(session_id, "error", {
                    "error": f"Error resolving persona: {str(persona_error)}",
                    "session_id": session_id
                })
                return

        logger.debug(f"Resolved system prompt: {len(resolved_system_prompt)} chars")

        # Stage 2: GENERATING - Stream main AI response (Stage 3)
        await ws_manager.broadcast_chunk(session_id, "stage_update", {
            "stage": ProcessingStage.GENERATING.value,
            "message": "Generating AI response..."
        })

        # Create provider instance
        provider_type = ProviderType.OLLAMA if provider_str == "ollama" else ProviderType.OPENAI
        provider = ProviderFactory.create_provider(provider_type)

        # Build chat request for Stage 3
        chat_request = ChatRequest(
            message=user_message,
            provider_type=provider_type,
            provider_settings=provider_settings,
            chat_controls=chat_controls,
            system_prompt=resolved_system_prompt
        )

        # Stream AI response with cancellation support
        accumulated_response = ""
        thinking_content = None
        response_metadata = {}

        async for chunk in provider.send_message_stream(chat_request, cancellation_token=cancellation_token):
            # Check cancellation
            if cancellation_token and cancellation_token.is_cancelled():
                logger.info(f"Streaming cancelled for session {session_id}")
                await ws_manager.broadcast_chunk(session_id, "cancelled", {
                    "session_id": session_id,
                    "message": "⏹️ Message generation was stopped"
                })
                return

            # Accumulate content
            if chunk.content:
                accumulated_response += chunk.content

            # Extract thinking if present
            if hasattr(chunk, 'thinking') and chunk.thinking:
                thinking_content = chunk.thinking

            # Extract metadata from final chunk
            if chunk.done:
                response_metadata = chunk.metadata or {}

            # Send chunk to client
            await ws_manager.broadcast_chunk(session_id, "chunk", {
                "content": chunk.content,
                "thinking": chunk.thinking if hasattr(chunk, 'thinking') else None,
                "done": chunk.done,
                "metadata": chunk.metadata if chunk.done else None
            })

        logger.debug(f"AI response complete: {len(accumulated_response)} chars")

        # Send done message immediately so frontend can display the message
        # POST_RESPONSE modules will run in background without blocking UI
        await ws_manager.broadcast_chunk(session_id, "done", {
            "metadata": response_metadata
        })

        # Stage 3: THINKING_AFTER - Execute POST_RESPONSE modules (Stages 4-5)
        # This runs AFTER done message, so it doesn't block UI
        if persona_id:
            try:
                # Send stage update BEFORE starting POST_RESPONSE so frontend knows it's running
                await ws_manager.broadcast_chunk(session_id, "stage_update", {
                    "stage": ProcessingStage.THINKING_AFTER.value,
                    "message": "Executing post-response modules..."
                })

                # Execute POST_RESPONSE stages asynchronously in background
                results = await resolver.execute_post_response_stages(
                    template=resolved_system_prompt,
                    ai_response=accumulated_response,
                    session_id=chat_session_id,  # Use chat session ID
                    conversation_id=conversation_id,
                    persona_id=persona_id,
                    db_session=db,
                    trigger_context={},
                    current_provider=provider_str,
                    current_provider_settings=provider_settings,
                    current_chat_controls=chat_controls
                )

                if results:
                    logger.info(f"Executed {len(results)} POST_RESPONSE modules for session {session_id}")
                    # Note: Commit happens at top-level chat_task, not here

                # Send completion message for POST_RESPONSE (whether or not modules ran)
                await ws_manager.broadcast_chunk(session_id, "post_response_complete", {
                    "message": "Background processing complete",
                    "chat_session_id": chat_session_id
                })

            except Exception as post_error:
                logger.error(f"POST_RESPONSE error for {session_id}: {post_error}")
                # Rollback database changes on POST_RESPONSE error
                db.rollback()
                # Non-fatal - POST_RESPONSE errors don't affect main response
                # Still send completion message
                await ws_manager.broadcast_chunk(session_id, "post_response_complete", {
                    "message": "Background processing complete (with errors)",
                    "chat_session_id": chat_session_id
                })

    except asyncio.CancelledError:
        logger.info(f"⏹️ Chat handler cancelled for chat session {chat_session_id}")
        await ws_manager.broadcast_chunk(session_id, "cancelled", {
            "message": "⏹️ Message generation was stopped",
            "session_id": session_id
        })
        raise

    except Exception as e:
        logger.error(f"❌ Error handling chat for WebSocket {session_id}, chat session {chat_session_id}: {e}", exc_info=True)
        await ws_manager.broadcast_chunk(session_id, "error", {
            "error": str(e),
            "session_id": session_id
        })

    finally:
        # Clean up the chat session (not the WebSocket session)
        await session_manager.complete_session(chat_session_id)


async def handle_cancel_request(
    session_id: str,
    ws_session_id: str,
    session_manager: ChatSessionManager,
    ws_manager: WebSocketManager
):
    """
    Handle cancel request received over WebSocket.

    This provides immediate cancellation by sending the cancel signal
    over the same connection, avoiding HTTP request queuing.

    Args:
        session_id: Chat session ID to cancel (for cancellation token)
        ws_session_id: WebSocket session ID (for sending response)
        session_manager: Chat session manager
        ws_manager: WebSocket manager for sending confirmation
    """

    logger.info(f"🛑 WebSocket cancel request for chat session {session_id}")

    try:
        # Cancel the chat session
        success = await session_manager.cancel_session(session_id)

        if success:
            logger.info(f"✅ Cancelled chat session {session_id} via WebSocket")
            await ws_manager.broadcast_chunk(ws_session_id, "cancelled", {
                "message": "Session cancelled successfully",
                "session_id": ws_session_id
            })
        else:
            logger.warning(f"⚠️ Failed to cancel session {session_id} - not found or already finished")
            await ws_manager.broadcast_chunk(ws_session_id, "error", {
                "error": "Session not found or already finished",
                "session_id": ws_session_id
            })

    except Exception as e:
        logger.error(f"❌ Error cancelling session {session_id}: {e}")
        await ws_manager.broadcast_chunk(ws_session_id, "error", {
            "error": f"Cancel error: {str(e)}",
            "session_id": ws_session_id
        })
