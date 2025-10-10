# Core Layer

The Core layer provides the foundational systems for advanced module execution, including script sandboxing, plugin infrastructure, and script analysis. This is the heart of Project 2501's cognitive system architecture.

## 📁 Files Overview

### [script_engine.py](script_engine.py)
**Secure Python script execution engine using RestrictedPython**

Provides safe execution of user-provided Python scripts for advanced modules.

**Key Features:**
- **RestrictedPython Sandbox**: Secure execution environment with restricted builtins
- **Timeout Handling**: 30-second default timeout (increased for AI reflection)
- **Safe Builtins**: Curated set of safe functions (math, types, utility, exceptions)
- **Allowed Modules**: Whitelist of importable modules (datetime, math, json, re, uuid, random, time)
- **Output Extraction**: Automatic extraction of script output variables
- **Guard Functions**: Security guards for attribute access, iteration, and imports

**Classes:**
- `ScriptExecutionResult`: Dataclass with success status, outputs, error message, execution time
- `ScriptExecutionError`: Custom exception for script failures
- `ScriptEngine`: Main execution engine with security validation

**Execution Flow:**
1. Compile script with RestrictedPython
2. Prepare safe execution environment
3. Inject security guards and restricted imports
4. Execute with timeout monitoring
5. Extract output variables (filters internal/temp variables)
6. Return structured result

**Security Features:**
- Blocks access to `_private` attributes
- Restricts imports to whitelist
- No file system access
- No network access
- No dangerous builtins (eval, exec, compile, open)

**Usage:**
```python
engine = ScriptEngine()
context = {'ctx': ScriptExecutionContext(...)}
result = engine.execute_script(script, context)
```

---

### [script_context.py](script_context.py)
**Execution context object for advanced module scripts**

Provides the `ctx` object that scripts receive, giving access to conversation data, plugins, and reflection capabilities.

**Key Features:**
- **Plugin Function Access**: Auto-injection of db_session and script context
- **Variable Storage**: User-defined variables for template substitution
- **Reflection Safety**: Depth tracking and chain management to prevent infinite loops
- **SystemPromptState Integration**: Optional state tracking for AI awareness
- **Provider Context**: Access to current AI provider and settings

**Reflection Safety:**
- `MAX_REFLECTION_DEPTH = 3`: Maximum nesting depth
- `MAX_REFLECTION_CHAIN_LENGTH = 10`: Maximum chain history
- `can_reflect()`: Safety check before allowing AI inference
- `enter_reflection()` / `exit_reflection()`: Depth tracking
- Module resolution stack to prevent circular dependencies

**Key Methods:**
```python
ctx.set_variable(name, value)         # Store output variable
ctx.get_variable(name, default)        # Retrieve variable
ctx.get_all_variables()                # Get all for template substitution
ctx.can_reflect(module_id, timing)     # Check reflection safety
ctx.enter_reflection(module_id, inst)  # Enter reflection mode
ctx.exit_reflection()                  # Exit reflection mode
ctx.get_reflection_audit_trail()       # Get audit trail
```

**Plugin Access:**
```python
ctx.get_current_time()        # Auto-injects db_session
ctx.generate(instructions)     # AI generation
ctx.reflect(prompt)            # AI reflection
```

---

### [script_plugins.py](script_plugins.py)
**Plugin registry system with auto-discovery**

Provides decorator-based registration for plugin functions that scripts can call.

**Key Features:**
- **Decorator Registration**: `@plugin_registry.register("function_name")`
- **Auto-Discovery**: Automatically loads all plugins from `app.plugins` package
- **Thread-Safe Loading**: Lock-based concurrent loading protection
- **Global Registry**: Single registry instance for entire application

**Usage:**
```python
# In plugin file (e.g., app/plugins/time_functions.py)
from app.core.script_plugins import plugin_registry

@plugin_registry.register("get_current_time")
def get_current_time(format_str: str = "%Y-%m-%d %H:%M:%S"):
    return datetime.now().strftime(format_str)

# Plugins auto-loaded on first use
plugin_registry.load_all_plugins()
```

**Registry Methods:**
```python
plugin_registry.register(name)         # Decorator for registration
plugin_registry.get_context()          # Get all registered functions
plugin_registry.load_all_plugins()     # Auto-discover and load
plugin_registry.clear()                # Clear registry (testing)
plugin_registry.get_registered_functions()  # Get function info
```

---

### [script_analyzer.py](script_analyzer.py)
**Static analysis for module script classification**

Analyzes Python scripts to detect AI dependencies, complexity, and characteristics for staged execution.

**Key Features:**
- **AST Parsing**: Accurate analysis using Python abstract syntax tree
- **AI Detection**: Identifies `generate()` and `reflect()` calls
- **Complexity Estimation**: Low/medium/high based on lines, functions, control flow
- **Regex Fallback**: Fallback analysis for syntax errors
- **Detailed Metrics**: Line count, function count, loops, conditionals

**Analysis Result:**
```python
@dataclass
class ScriptAnalysisResult:
    requires_ai_inference: bool        # Needs AI provider
    uses_generate: bool                # Uses generate()
    uses_reflect: bool                 # Uses reflect()
    uses_other_plugins: bool           # Uses non-AI plugins
    detected_functions: List[str]      # All detected ctx.* calls
    ai_function_calls: List[str]       # AI-specific calls
    plugin_function_calls: List[str]   # Non-AI plugin calls
    estimated_complexity: str          # "low", "medium", "high"
    line_count: int                    # Non-empty lines
    function_count: int                # Total function calls
    has_loops: bool                    # Contains for/while loops
    has_conditionals: bool             # Contains if statements
    analysis_success: bool             # Analysis completed successfully
    error_message: Optional[str]       # Error if failed
```

**Complexity Scoring:**
- Line count: 0-1 points (5/20/50+ lines)
- Function calls: 0-3 points (2/5/10+ calls)
- Control flow: +2 for loops, +1 for conditionals
- **Low**: 0-2 points
- **Medium**: 3-5 points
- **High**: 6+ points

**Usage:**
```python
from app.core.script_analyzer import analyze_module_script

result = analyze_module_script(script_code)
if result.requires_ai_inference:
    # Execute in Stage 2 or Stage 5
else:
    # Execute in Stage 1 or Stage 4
```

---

### [trigger_matcher.py](trigger_matcher.py)
**Pattern matching for advanced module execution triggers**

Determines when advanced modules should execute based on trigger patterns and context.

**Supported Patterns:**
- `None` or `""`: Always execute
- `"*"`: Always execute
- `"keyword"`: Case-insensitive keyword search
- `"word1|word2|word3"`: OR pattern - matches any option
- `r"\bregex\b"`: Regex pattern matching (case insensitive)

**Key Methods:**
```python
TriggerMatcher.should_execute(pattern, context)  # Check if should execute
TriggerMatcher.validate_pattern(pattern)         # Validate pattern syntax
TriggerMatcher.get_pattern_type(pattern)         # Get pattern type info
```

**Example Usage:**
```python
trigger_context = {"last_user_message": "Hello, what time is it?"}

# Always execute
TriggerMatcher.should_execute("*", trigger_context)  # True

# Keyword matching
TriggerMatcher.should_execute("time", trigger_context)  # True

# OR pattern
TriggerMatcher.should_execute("time|date|clock", trigger_context)  # True

# Regex
TriggerMatcher.should_execute(r"\btime\b", trigger_context)  # True
```

**Pattern Matching Flow:**
1. Check for always-execute patterns (`*`, `None`, `""`)
2. Extract `last_user_message` from context
3. Try regex compilation and matching
4. Fall back to simple string containment
5. Handle OR patterns (pipe-separated)

---

### [config.py](config.py) *(if present)*
**Configuration settings for core systems**

Environment variables, default timeouts, security settings.

---

## 🏗️ Architecture Integration

### Script Execution Flow
```
Advanced Module → ScriptEngine → RestrictedPython Sandbox → Plugin Functions
                     ↓                                              ↓
              ScriptContext (ctx)  ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
                     ↓
         Output Variables → Template Substitution
```

### Plugin System Flow
```
App Startup → plugin_registry.load_all_plugins()
                     ↓
            Scan app/plugins/* modules
                     ↓
            Import and register @decorated functions
                     ↓
            Store in global registry
                     ↓
    ScriptContext.__getattr__ → Auto-inject db_session → Execute
```

### Analysis Integration
```
Module Creation/Update → script_analyzer.analyze_script()
                                   ↓
                    Detect AI dependencies (generate/reflect)
                                   ↓
                    Set requires_ai_inference flag
                                   ↓
            Stage 1/4 (Non-AI) or Stage 2/5 (AI) execution
```

---

## 🔐 Security Model

### RestrictedPython Sandbox
1. **Compilation**: RestrictedPython compiles code with restrictions
2. **Safe Builtins**: Only whitelisted functions available
3. **Import Restrictions**: Only allowed modules can be imported
4. **Attribute Guards**: Block access to private attributes
5. **No I/O**: File system and network access blocked
6. **No Eval**: eval/exec/compile not available

### Reflection Safety
1. **Depth Limiting**: Max 3 levels of nested AI calls
2. **Circular Prevention**: Module resolution stack tracking
3. **Chain History**: Audit trail of reflection calls
4. **Context Blocking**: IMMEDIATE modules can't reflect in nested contexts

---

## 🧪 Testing Considerations

### Script Engine Testing
- Empty script handling
- Syntax error handling
- Timeout enforcement
- Output variable extraction
- Security validation
- Import restrictions

### Script Context Testing
- Variable storage/retrieval
- Plugin function injection
- Reflection safety checks
- Depth tracking
- Resolution stack management
- Audit trail generation

### Analyzer Testing
- AI function detection
- Complexity estimation
- AST parsing errors
- Regex fallback
- Empty script handling

### Trigger Matcher Testing
- Always patterns
- Keyword matching
- OR patterns
- Regex patterns
- Invalid patterns
- Case sensitivity

---

## 📊 Performance Considerations

### Script Execution
- **Compilation Caching**: RestrictedPython compiles once per execution
- **Timeout Monitoring**: 30-second default (configurable)
- **Output Extraction**: Filters to reduce overhead

### Plugin Loading
- **Lazy Loading**: Plugins loaded on first use
- **Thread Safety**: Lock prevents concurrent loading issues
- **Module Caching**: Python imports cached by interpreter

### Analysis Performance
- **AST Parsing**: Fast for most scripts (<100ms)
- **Regex Fallback**: Used only on syntax errors
- **Result Caching**: Analysis results stored in database

---

## 📝 Notes

- All scripts run in isolated RestrictedPython sandbox
- Plugin functions automatically receive db_session parameter
- Reflection depth tracked to prevent infinite loops
- Script analysis performed on module create/update
- Trigger patterns support regex with case-insensitive matching
- Empty/None trigger patterns mean "always execute"
