"""
Module database model for storing cognitive system modules.
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from .base import Base


class ModuleType(str, enum.Enum):
    """Enumeration of module types."""
    SIMPLE = "simple"
    ADVANCED = "advanced"


class ExecutionContext(str, enum.Enum):
    """Enumeration of module execution contexts for staged pipeline."""
    IMMEDIATE = "IMMEDIATE"      # Execute during template resolution (Stage 1-2)
    POST_RESPONSE = "POST_RESPONSE"  # Execute after AI response (Stage 4-5)
    ON_DEMAND = "ON_DEMAND"      # Execute only when explicitly triggered

# Deprecated - kept for migration compatibility, will be removed
class ExecutionTiming(str, enum.Enum):
    """DEPRECATED: Use ExecutionContext instead."""
    BEFORE = "before"
    AFTER = "after"
    CUSTOM = "custom"


class Module(Base):
    """
    Module model representing a cognitive system module.
    """
    __tablename__ = "modules"
    
    # Use UUID for module IDs
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Basic module information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Module content
    content = Column(Text, nullable=True)  # Static text for simple modules, Python code for advanced
    
    # Module type and behavior
    type = Column(SQLEnum(ModuleType), nullable=False, default=ModuleType.SIMPLE)
    
    # Advanced module configuration (only for advanced modules)
    trigger_pattern = Column(String(500), nullable=True)  # Regex or keyword pattern for activation
    script = Column(Text, nullable=True)  # Python script content for advanced modules
    
    # Staged execution configuration
    execution_context = Column(SQLEnum(ExecutionContext), nullable=False, default=ExecutionContext.ON_DEMAND)
    requires_ai_inference = Column(Boolean, default=False, nullable=False)  # Auto-detected from script analysis
    script_analysis_metadata = Column(JSON, nullable=True, default=dict)  # Analysis results and metadata
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self) -> str:
        return f"<Module(id={self.id}, name='{self.name}', type='{self.type}', context='{self.execution_context}')>"
    
    def analyze_script(self) -> dict:
        """
        Analyze the module script to detect AI dependencies and characteristics.
        
        Returns:
            Dictionary with analysis results, or empty dict if no script
        """
        if not self.script or self.type != ModuleType.ADVANCED:
            return {}
        
        from ..core.script_analyzer import analyze_module_script
        
        analysis_result = analyze_module_script(self.script)
        analysis_dict = analysis_result.to_dict()
        
        # Update the requires_ai_inference field based on analysis
        self.requires_ai_inference = analysis_result.requires_ai_inference
        self.script_analysis_metadata = analysis_dict
        
        return analysis_dict
    
    def refresh_ai_analysis(self, db_session=None):
        """
        Re-analyze the script and update AI dependency fields.
        
        Args:
            db_session: Optional database session for committing changes
        """
        if self.type == ModuleType.ADVANCED and self.script:
            analysis = self.analyze_script()
            
            if db_session:
                db_session.flush()  # Persist the changes from analyze_script()
    
    @property
    def is_immediate_context(self) -> bool:
        """Check if module executes in IMMEDIATE context (during template resolution)."""
        return self.execution_context == ExecutionContext.IMMEDIATE
    
    @property
    def is_post_response_context(self) -> bool:
        """Check if module executes in POST_RESPONSE context (after AI response)."""
        return self.execution_context == ExecutionContext.POST_RESPONSE
    
    @property
    def is_on_demand_context(self) -> bool:
        """Check if module executes in ON_DEMAND context (only when triggered)."""
        return self.execution_context == ExecutionContext.ON_DEMAND
    
    @property
    def execution_stage_priority(self) -> int:
        """
        Get the stage priority for execution ordering.
        
        Returns:
            Integer priority: lower numbers execute first
        """
        if self.execution_context == ExecutionContext.IMMEDIATE:
            return 1 if not self.requires_ai_inference else 2
        elif self.execution_context == ExecutionContext.POST_RESPONSE:
            return 4 if not self.requires_ai_inference else 5
        else:  # ON_DEMAND
            return 999  # Only execute when explicitly triggered
    
    def get_stage_name(self) -> str:
        """
        Get human-readable stage name for UI display.
        
        Returns:
            String describing when this module executes
        """
        if self.execution_context == ExecutionContext.IMMEDIATE:
            if self.requires_ai_inference:
                return "Stage 2: Pre-response AI processing"
            else:
                return "Stage 1: Template preparation"
        elif self.execution_context == ExecutionContext.POST_RESPONSE:
            if self.requires_ai_inference:
                return "Stage 5: Post-response AI analysis"
            else:
                return "Stage 4: Post-response processing"
        else:
            return "On-demand execution"
    
    @classmethod
    def get_modules_for_stage(cls, db_session, stage_number: int, persona_id: str = None):
        """
        Get modules that should execute in a specific stage.
        
        Args:
            db_session: Database session
            stage_number: Stage number (1, 2, 4, 5)
            persona_id: Optional persona ID to filter modules used by a persona
            
        Returns:
            Query object for modules in the specified stage
        """
        query = db_session.query(cls).filter(cls.is_active == True)
        
        if stage_number == 1:
            # Stage 1: Simple modules (always execute) OR IMMEDIATE context with no AI inference OR POST_RESPONSE modules (for previous state resolution)
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    cls.type == ModuleType.SIMPLE,  # All simple modules execute in Stage 1
                    (cls.execution_context == ExecutionContext.IMMEDIATE) & (cls.requires_ai_inference == False),
                    cls.execution_context == ExecutionContext.POST_RESPONSE  # Include for previous state resolution
                )
            )
        elif stage_number == 2:
            # Stage 2: IMMEDIATE context, requires AI inference
            query = query.filter(
                cls.execution_context == ExecutionContext.IMMEDIATE,
                cls.requires_ai_inference == True
            )
        elif stage_number == 4:
            # Stage 4: POST_RESPONSE context, no AI inference
            query = query.filter(
                cls.execution_context == ExecutionContext.POST_RESPONSE,
                cls.requires_ai_inference == False
            )
        elif stage_number == 5:
            # Stage 5: POST_RESPONSE context, requires AI inference
            query = query.filter(
                cls.execution_context == ExecutionContext.POST_RESPONSE,
                cls.requires_ai_inference == True
            )
        else:
            # Invalid stage number
            return query.filter(False)  # Return empty query
        
        # If persona_id is provided, only return modules referenced in that persona's template
        if persona_id:
            from .persona import Persona
            persona = db_session.query(Persona).filter(Persona.id == persona_id).first()
            if persona and persona.template:
                # Parse module references from template (simplified - the resolver has the full logic)
                import re
                module_refs = re.findall(r'@([a-z][a-z0-9_]*)', persona.template)
                if module_refs:
                    query = query.filter(cls.name.in_(module_refs))
                else:
                    return query.filter(False)  # No module references found
        
        return query.order_by(cls.name)