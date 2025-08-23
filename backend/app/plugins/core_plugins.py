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


@plugin_registry.register("clean_text")
def clean_text(text: str, remove_extra_whitespace: bool = True, 
               remove_newlines: bool = False) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Text to clean
        remove_extra_whitespace: Remove extra spaces and normalize whitespace
        remove_newlines: Remove newline characters
        
    Returns:
        Cleaned text
        
    Example:
        clean_text("  hello   world  ") -> "hello world"
        clean_text("hello\\nworld", remove_newlines=True) -> "hello world"
    """
    if remove_newlines:
        text = text.replace('\n', ' ').replace('\r', ' ')
    
    if remove_extra_whitespace:
        text = re.sub(r'\s+', ' ', text).strip()
    
    return text


@plugin_registry.register("truncate_text")
def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated (default: "...")
        
    Returns:
        Truncated text
        
    Example:
        truncate_text("Hello world", 8) -> "Hello..."
        truncate_text("Hello world", 8, "..") -> "Hello .."
    """
    if len(text) <= max_length:
        return text
    
    if len(suffix) >= max_length:
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


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


@plugin_registry.register("extract_numbers")
def extract_numbers(text: str) -> List[float]:
    """
    Extract all numbers from text.
    
    Args:
        text: Text to extract numbers from
        
    Returns:
        List of numbers found in text
        
    Example:
        extract_numbers("I have 5 apples and 3.5 oranges") -> [5.0, 3.5]
    """
    pattern = r'-?\d+(?:\.\d+)?'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches]


@plugin_registry.register("safe_divide")
def safe_divide(numerator: Union[int, float], denominator: Union[int, float], 
                default: Union[int, float] = 0) -> Union[int, float]:
    """
    Safely divide two numbers, returning default if division by zero.
    
    Args:
        numerator: Number to divide
        denominator: Number to divide by
        default: Value to return if division by zero (default: 0)
        
    Returns:
        Division result or default value
        
    Example:
        safe_divide(10, 2) -> 5.0
        safe_divide(10, 0) -> 0
        safe_divide(10, 0, -1) -> -1
    """
    if denominator == 0:
        return default
    return numerator / denominator