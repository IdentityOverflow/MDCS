"""
Unit tests for the Trigger Pattern Matching System.

Tests the simple trigger matching logic for determining when advanced modules
should execute based on keyword/regex patterns and conversation context.
"""

import pytest
from app.core.trigger_matcher import TriggerMatcher


class TestTriggerMatcher:
    """Test cases for the TriggerMatcher class."""

    def test_no_pattern_always_executes(self):
        """Test that no pattern (None or empty) always returns True."""
        trigger_context = {"last_user_message": "Hello world"}
        
        assert TriggerMatcher.should_execute(None, trigger_context) is True
        assert TriggerMatcher.should_execute("", trigger_context) is True
        assert TriggerMatcher.should_execute("   ", trigger_context) is True

    def test_always_pattern_executes(self):
        """Test that '*' pattern always executes."""
        trigger_context = {"last_user_message": "Hello world"}
        
        assert TriggerMatcher.should_execute("*", trigger_context) is True
        
        # Should work even with empty context
        assert TriggerMatcher.should_execute("*", {}) is True

    def test_simple_keyword_matching_case_insensitive(self):
        """Test simple keyword matching (case insensitive)."""
        trigger_context = {"last_user_message": "Hello WORLD how are you"}
        
        # Case insensitive matching
        assert TriggerMatcher.should_execute("hello", trigger_context) is True
        assert TriggerMatcher.should_execute("HELLO", trigger_context) is True
        assert TriggerMatcher.should_execute("world", trigger_context) is True
        assert TriggerMatcher.should_execute("World", trigger_context) is True
        
        # Should not match non-existent words
        assert TriggerMatcher.should_execute("goodbye", trigger_context) is False

    def test_or_pattern_matching(self):
        """Test OR pattern matching with pipe separator."""
        trigger_context = {"last_user_message": "I need to remember something important"}
        
        # Should match any of the OR options
        assert TriggerMatcher.should_execute("memory|remember|recall", trigger_context) is True
        assert TriggerMatcher.should_execute("forget|remember|think", trigger_context) is True
        assert TriggerMatcher.should_execute("memory|recall|think", trigger_context) is False
        
        # Test with mixed case
        assert TriggerMatcher.should_execute("MEMORY|REMEMBER|RECALL", trigger_context) is True

    def test_or_pattern_with_whitespace(self):
        """Test OR pattern matching handles whitespace properly."""
        trigger_context = {"last_user_message": "What is the weather like"}
        
        # Should handle spaces around pipe
        assert TriggerMatcher.should_execute("weather | climate | temperature", trigger_context) is True
        assert TriggerMatcher.should_execute("rain | weather| snow", trigger_context) is True
        assert TriggerMatcher.should_execute("sun|  clouds  |weather", trigger_context) is True

    def test_regex_pattern_matching(self):
        """Test regex pattern matching."""
        trigger_context = {"last_user_message": "What did I say earlier today?"}
        
        # Word boundary regex
        assert TriggerMatcher.should_execute(r"\bwhat did\b", trigger_context) is True
        assert TriggerMatcher.should_execute(r"\bearlier\b", trigger_context) is True
        
        # Pattern that shouldn't match
        assert TriggerMatcher.should_execute(r"\byesterday\b", trigger_context) is False
        
        # More complex regex
        assert TriggerMatcher.should_execute(r"what.*earlier", trigger_context) is True

    def test_regex_case_insensitive(self):
        """Test that regex matching is case insensitive."""
        trigger_context = {"last_user_message": "HELLO WORLD"}
        
        assert TriggerMatcher.should_execute(r"hello.*world", trigger_context) is True
        assert TriggerMatcher.should_execute(r"HELLO.*WORLD", trigger_context) is True
        assert TriggerMatcher.should_execute(r"Hello.*World", trigger_context) is True

    def test_invalid_regex_falls_back_to_string_matching(self):
        """Test that invalid regex patterns fall back to string containment."""
        trigger_context = {"last_user_message": "Hello [world] how are you"}
        
        # Invalid regex pattern (unmatched bracket)
        invalid_pattern = r"hello [world"
        assert TriggerMatcher.should_execute(invalid_pattern, trigger_context) is True
        
        # Should fall back to string containment (case insensitive)
        assert TriggerMatcher.should_execute("hello [world", trigger_context) is True
        assert TriggerMatcher.should_execute("HELLO [WORLD", trigger_context) is True

    def test_empty_last_user_message(self):
        """Test behavior with empty last user message."""
        trigger_context = {"last_user_message": ""}
        
        # Should not match any keyword
        assert TriggerMatcher.should_execute("hello", trigger_context) is False
        assert TriggerMatcher.should_execute("memory|remember", trigger_context) is False
        
        # Always pattern should still match
        assert TriggerMatcher.should_execute("*", trigger_context) is True
        assert TriggerMatcher.should_execute(None, trigger_context) is True

    def test_missing_last_user_message_key(self):
        """Test behavior when last_user_message key is missing from context."""
        trigger_context = {"some_other_key": "value"}
        
        # Should not match any pattern (treats as empty message)
        assert TriggerMatcher.should_execute("hello", trigger_context) is False
        assert TriggerMatcher.should_execute("memory|remember", trigger_context) is False
        
        # Always pattern should still match
        assert TriggerMatcher.should_execute("*", trigger_context) is True
        assert TriggerMatcher.should_execute(None, trigger_context) is True

    def test_complex_trigger_patterns(self):
        """Test various complex trigger patterns."""
        
        # Test technical terms
        trigger_context = {"last_user_message": "Can you help me debug this API error?"}
        assert TriggerMatcher.should_execute("debug|error|bug|issue", trigger_context) is True
        assert TriggerMatcher.should_execute("api|database|server", trigger_context) is True
        
        # Test emotional context
        trigger_context = {"last_user_message": "I'm feeling frustrated with this task"}
        assert TriggerMatcher.should_execute("frustrated|angry|upset|annoyed", trigger_context) is True
        assert TriggerMatcher.should_execute("feeling|emotion|mood", trigger_context) is True
        
        # Test time-related
        trigger_context = {"last_user_message": "What time is it right now?"}
        assert TriggerMatcher.should_execute("time|clock|now|current", trigger_context) is True
        assert TriggerMatcher.should_execute(r"\btime\b|\bnow\b", trigger_context) is True

    def test_exact_word_matching_with_regex(self):
        """Test exact word matching using regex word boundaries."""
        trigger_context = {"last_user_message": "I need to create a new creation"}
        
        # Should match both "create" and "creation" as whole words
        assert TriggerMatcher.should_execute(r"\bcreate\b", trigger_context) is True
        assert TriggerMatcher.should_execute(r"\bcreation\b", trigger_context) is True
        
        # Should NOT match partial words  
        trigger_context_2 = {"last_user_message": "I need to creating something"}
        assert TriggerMatcher.should_execute(r"\bcreate\b", trigger_context_2) is False
        assert TriggerMatcher.should_execute(r"\bcreation\b", trigger_context_2) is False
        
        # Without word boundaries, partial matches should work
        assert TriggerMatcher.should_execute("creat", trigger_context_2) is True

    def test_special_characters_in_patterns(self):
        """Test patterns containing special characters."""
        trigger_context = {"last_user_message": "What's the cost? It's $50.99"}
        
        # Simple patterns without regex special chars should work
        assert TriggerMatcher.should_execute("what's", trigger_context) is True
        assert TriggerMatcher.should_execute("cost", trigger_context) is True
        
        # Patterns with regex special chars might not work as expected
        # $50 is interpreted as regex (end of line + 50) so it won't match
        assert TriggerMatcher.should_execute("$50", trigger_context) is False
        
        # To match literal $50, need to escape it or use string that doesn't compile as regex
        assert TriggerMatcher.should_execute(r"\$50", trigger_context) is True
        
        # Pattern that fails regex compilation falls back to string matching
        assert TriggerMatcher.should_execute("[unclosed", trigger_context) is False  # This text not in message

    def test_unicode_and_special_text(self):
        """Test patterns with unicode and special text."""
        trigger_context = {"last_user_message": "Hello 👋 how are you today? ¿Cómo estás?"}
        
        # Should handle unicode in both pattern and message
        assert TriggerMatcher.should_execute("hello", trigger_context) is True
        assert TriggerMatcher.should_execute("👋", trigger_context) is True
        assert TriggerMatcher.should_execute("cómo", trigger_context) is True
        assert TriggerMatcher.should_execute("estás", trigger_context) is True

    def test_very_long_messages(self):
        """Test trigger matching on very long messages."""
        long_message = "This is a very long message. " * 100 + "The keyword is hidden here."
        trigger_context = {"last_user_message": long_message}
        
        assert TriggerMatcher.should_execute("keyword", trigger_context) is True
        assert TriggerMatcher.should_execute("hidden", trigger_context) is True
        assert TriggerMatcher.should_execute("nonexistent", trigger_context) is False

    def test_performance_edge_cases(self):
        """Test edge cases that might affect performance."""
        # Empty strings
        trigger_context = {"last_user_message": ""}
        assert TriggerMatcher.should_execute("", trigger_context) is True  # Empty pattern
        
        # Very long pattern
        long_pattern = "|".join([f"word{i}" for i in range(100)])
        trigger_context = {"last_user_message": "word50 is here"}
        assert TriggerMatcher.should_execute(long_pattern, trigger_context) is True