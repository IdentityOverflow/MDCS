"""
Trigger Pattern Matching for Advanced Modules.

Provides simple pattern matching logic to determine when advanced modules
should execute based on conversation context and trigger patterns.
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TriggerMatcher:
    """
    Simple trigger pattern matching for advanced modules.
    
    Supports keyword matching, OR patterns with '|', regex patterns,
    and always-execute patterns.
    """
    
    @staticmethod
    def should_execute(trigger_pattern: Optional[str], trigger_context: Dict[str, Any]) -> bool:
        """
        Check if module should execute based on trigger pattern and context.
        
        Args:
            trigger_pattern: Pattern to match against (None, empty, '*', keyword, regex)
            trigger_context: Context dictionary with conversation data
            
        Returns:
            True if module should execute based on pattern matching
            
        Pattern types supported:
            - None or empty string: Always execute
            - "*": Always execute 
            - "keyword": Simple case-insensitive keyword matching
            - "word1|word2|word3": OR pattern - matches any of the words
            - r"regex_pattern": Regex pattern matching (case insensitive)
        """
        # No pattern or empty pattern means always execute
        if not trigger_pattern or not trigger_pattern.strip():
            return True
        
        # Always execute pattern
        if trigger_pattern.strip() == "*":
            return True
        
        # Get the last user message for pattern matching
        last_message = trigger_context.get("last_user_message", "")
        if not last_message:
            return False  # No message to match against
        
        # Convert to lowercase for case-insensitive matching
        last_message_lower = last_message.lower()
        
        # Check for OR pattern (contains |) - but handle regex OR patterns too
        if "|" in trigger_pattern:
            # First try as regex (might be regex OR pattern like \bword1\b|\bword2\b)
            try:
                pattern = re.compile(trigger_pattern, re.IGNORECASE)
                match_result = bool(pattern.search(last_message))
                logger.debug(f"Regex OR pattern '{trigger_pattern}' matched: {match_result}")
                return match_result
            except re.error:
                # If regex fails, treat as simple OR pattern
                return TriggerMatcher._match_or_pattern(trigger_pattern, last_message_lower)
        
        # Try regex pattern matching
        try:
            pattern = re.compile(trigger_pattern, re.IGNORECASE)
            match_result = bool(pattern.search(last_message))
            logger.debug(f"Regex pattern '{trigger_pattern}' matched: {match_result}")
            return match_result
            
        except re.error:
            # If regex fails, fall back to simple string containment
            logger.debug(f"Invalid regex '{trigger_pattern}', falling back to string matching")
            return TriggerMatcher._match_simple_string(trigger_pattern, last_message_lower)
    
    @staticmethod
    def _match_or_pattern(pattern: str, message_lower: str) -> bool:
        """
        Match OR pattern with pipe separator.
        
        Args:
            pattern: Pattern with pipe separators (e.g., "word1|word2|word3")
            message_lower: Lowercase message to search in
            
        Returns:
            True if any of the OR options match
        """
        # Split by pipe and strip whitespace from each option
        options = [option.strip().lower() for option in pattern.split("|")]
        
        # Check if any option is contained in the message
        for option in options:
            if option and option in message_lower:
                logger.debug(f"OR pattern option '{option}' matched")
                return True
        
        logger.debug(f"No OR pattern options matched in: {options}")
        return False
    
    @staticmethod
    def _match_simple_string(pattern: str, message_lower: str) -> bool:
        """
        Match simple string containment (case insensitive).
        
        Args:
            pattern: Pattern string to search for
            message_lower: Lowercase message to search in
            
        Returns:
            True if pattern is contained in message
        """
        pattern_lower = pattern.lower()
        match_result = pattern_lower in message_lower
        logger.debug(f"Simple string pattern '{pattern}' matched: {match_result}")
        return match_result
    
    @staticmethod
    def validate_pattern(pattern: str) -> bool:
        """
        Validate that a trigger pattern is syntactically correct.
        
        Args:
            pattern: Trigger pattern to validate
            
        Returns:
            True if pattern is valid
        """
        if not pattern or pattern.strip() in ("", "*"):
            return True  # Empty and always patterns are valid
        
        # If it contains |, it's an OR pattern - just check it's not empty
        if "|" in pattern:
            options = [opt.strip() for opt in pattern.split("|")]
            return any(opt for opt in options)  # At least one non-empty option
        
        # Try to compile as regex - if it fails, it's still valid as string pattern
        try:
            re.compile(pattern, re.IGNORECASE)
            return True
        except re.error:
            # Invalid regex, but still valid as string pattern
            return True
    
    @staticmethod
    def get_pattern_type(pattern: str) -> str:
        """
        Get the type of pattern for informational purposes.
        
        Args:
            pattern: Trigger pattern to analyze
            
        Returns:
            String describing pattern type
        """
        if not pattern or not pattern.strip():
            return "always"
        
        if pattern.strip() == "*":
            return "always"
        
        if "|" in pattern:
            return "or_pattern"
        
        # Try to determine if it's a regex pattern
        try:
            re.compile(pattern)
            # If it contains regex special characters, likely intended as regex
            regex_chars = r"[.*+?^${}()|[\]\\"
            if any(char in pattern for char in regex_chars):
                return "regex"
            else:
                return "keyword"
        except re.error:
            return "keyword"