#!/usr/bin/env python3
"""
Simple test script to verify memory plugin registration.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.script_plugins import plugin_registry

def test_memory_plugins():
    """Test that all memory plugins are registered."""
    
    # Load all plugins first
    plugin_registry.load_all_plugins()
    
    # List of memory plugin functions that should be registered
    expected_plugins = [
        'get_buffer_messages',
        'should_compress_buffer', 
        'store_memory',
        'get_recent_memories',
        'get_memory_status'
    ]
    
    print("Testing memory plugin registration...")
    registered_plugins = plugin_registry.get_registered_functions()
    print(f"Total registered plugins: {len(registered_plugins)}")
    
    # Check each expected plugin
    for plugin_name in expected_plugins:
        if plugin_name in registered_plugins:
            print(f"✅ {plugin_name} is registered")
        else:
            print(f"❌ {plugin_name} is NOT registered")
    
    # List all registered plugins for debugging
    print("\nAll registered plugins:")
    for name in sorted(registered_plugins.keys()):
        print(f"  - {name}")

if __name__ == "__main__":
    test_memory_plugins()