"""
Core utility plugin functions for advanced modules.

Provides basic utility functions that can be used in advanced module scripts.
"""

import json
import re
from typing import Any, List, Dict, Union
from app.core.script_plugins import plugin_registry


@plugin_registry.register("to_json")
def to_json(data: Any, indent: int = None) -> str:
    """
    Convert data to JSON string.
    
    Args:
        data: Data to convert to JSON
        indent: JSON indentation (None for compact)
        
    Returns:
        JSON string representation
        
    Example:
        to_json({"name": "test"}) -> '{"name": "test"}'
        to_json({"name": "test"}, 2) -> formatted JSON with 2-space indent
    """
    return json.dumps(data, indent=indent, default=str)


@plugin_registry.register("from_json")
def from_json(json_str: str) -> Any:
    """
    Parse JSON string to Python object.
    
    Args:
        json_str: JSON string to parse
        
    Returns:
        Parsed Python object
        
    Example:
        from_json('{"name": "test"}') -> {"name": "test"}
    """
    return json.loads(json_str)


@plugin_registry.register("join_strings")
def join_strings(strings: List[str], separator: str = ", ") -> str:
    """
    Join a list of strings with separator.
    
    Args:
        strings: List of strings to join
        separator: Separator string (default: ", ")
        
    Returns:
        Joined string
        
    Example:
        join_strings(["a", "b", "c"]) -> "a, b, c"
        join_strings(["a", "b", "c"], " | ") -> "a | b | c"
    """
    return separator.join(strings)


@plugin_registry.register("split_string")
def split_string(text: str, separator: str = None, max_splits: int = -1) -> List[str]:
    """
    Split a string by separator.
    
    Args:
        text: Text to split
        separator: Separator to split on (None for whitespace)
        max_splits: Maximum number of splits (-1 for no limit)
        
    Returns:
        List of split strings
        
    Example:
        split_string("a,b,c", ",") -> ["a", "b", "c"]
        split_string("a b c") -> ["a", "b", "c"]
    """
    return text.split(separator, max_splits)

@plugin_registry.register("count_words")
def count_words(text: str) -> int:
    """
    Count the number of words in text.
    
    Args:
        text: Text to count words in
        
    Returns:
        Number of words
        
    Example:
        count_words("hello world") -> 2
        count_words("hello,  world!") -> 2
    """
    return len(text.split())