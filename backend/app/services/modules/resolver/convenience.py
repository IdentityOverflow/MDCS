"""
Convenience functions for backward compatibility with the resolver API.

These functions provide the same interface as the original monolithic resolver.py
for API endpoints and other modules that depend on them.
"""

import asyncio
import concurrent.futures
from typing import List, Optional
from sqlalchemy.orm import Session

from ....database.connection import get_db
from ..template_parser import TemplateParser
from .orchestrator import StagedModuleResolver
from .result_models import StagedTemplateResolutionResult


def resolve_template_for_response(
    template: str, 
    conversation_id: Optional[str] = None,
    persona_id: Optional[str] = None,
    db_session: Optional[Session] = None
) -> StagedTemplateResolutionResult:
    """
    Convenience function to resolve a template for main AI response (Stage 1 + Stage 2).
    
    If db_session is not provided, a new session will be obtained and closed.
    """
    local_db_session = None
    try:
        if db_session is None:
            local_db_session = next(get_db())
            db_session = local_db_session
            
        resolver = StagedModuleResolver(db_session=db_session)
        
        # Use asyncio.run to handle the async method
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a new thread
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        resolver.resolve_template_stages_1_and_2(
                            template=template,
                            conversation_id=conversation_id,
                            persona_id=persona_id,
                            db_session=db_session
                        )
                    )
                    return future.result()
            else:
                # No event loop running, we can use asyncio.run directly
                return asyncio.run(
                    resolver.resolve_template_stages_1_and_2(
                        template=template,
                        conversation_id=conversation_id,
                        persona_id=persona_id,
                        db_session=db_session
                    )
                )
        except RuntimeError:
            # Fallback: create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    resolver.resolve_template_stages_1_and_2(
                        template=template,
                        conversation_id=conversation_id,
                        persona_id=persona_id,
                        db_session=db_session
                    )
                )
            finally:
                loop.close()
    finally:
        if local_db_session:
            local_db_session.close()


def _parse_module_references(template: str) -> List[str]:
    """Parse module references from template for backward compatibility."""
    return TemplateParser.parse_module_references(template)