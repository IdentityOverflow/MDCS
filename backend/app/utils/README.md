# Utils Layer

The Utils layer is currently minimal and serves as a placeholder for future utility functions.

## 📁 Files Overview

### [__init__.py](__init__.py)
**Package initialization**

Empty file marking this as a Python package.

---

## 🎯 Purpose

The utils folder is reserved for:
- Common utility functions shared across multiple layers
- Helper functions that don't fit in other layers
- Cross-cutting concerns like logging formatters, validators, etc.

---

## 📝 Current Status

**Status**: Minimal/Placeholder

Currently, utility functions are distributed across:
- **Core utilities**: See [../core/](../core/) for script engine utilities
- **Service utilities**: See [../services/utils/](../services/utils/) for service-layer utilities
- **API utilities**: Inline within API endpoints

---

## 🔮 Potential Future Utilities

### Logging Utilities
```python
# Custom formatters for structured logging
def format_log_entry(level, message, context):
    pass

# Log context managers
@contextmanager
def log_execution_time(operation_name):
    pass
```

### Validation Utilities
```python
# UUID validation
def is_valid_uuid(uuid_string: str) -> bool:
    pass

# Email validation
def is_valid_email(email: str) -> bool:
    pass
```

### Formatting Utilities
```python
# Token count formatting
def format_token_count(count: int) -> str:
    pass

# Duration formatting
def format_duration(seconds: float) -> str:
    pass
```

### Data Transformation
```python
# Deep merge dictionaries
def deep_merge(dict1: dict, dict2: dict) -> dict:
    pass

# Flatten nested structures
def flatten_dict(nested: dict, sep: str = '.') -> dict:
    pass
```

---

## 📦 Related Utility Locations

### Core Utilities ([../core/](../core/))
- Script execution utilities
- Plugin registry
- Trigger matching
- Script analysis

### Service Utilities ([../services/utils/](../services/utils/))
- Async helpers
- Error handling
- Validation

### API Utilities (Inline)
- Request parsing
- Response formatting
- Error responses

---

## 📝 Notes

- Utils folder currently empty by design
- Utility functions organized in domain-specific locations
- Future utilities should be added here when they:
  - Are used across multiple layers
  - Don't belong to a specific domain
  - Provide cross-cutting functionality
