"""
Plugin package for advanced module script functions.

This package contains plugin modules that register functions for use in
advanced module scripts. Functions are registered using the @plugin_registry.register
decorator and are automatically discovered when plugins are loaded.
"""

# This file makes the plugins directory a Python package
# Plugin modules are auto-discovered and loaded by the ScriptPluginRegistry