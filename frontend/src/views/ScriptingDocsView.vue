<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

interface PluginFunction {
  name: string
  signature: string
  docstring: string
  category: string
  parameters: Array<{
    name: string
    type: string
    default?: string
    required: boolean
  }>
}

// Documentation sections
const sections = ref([
  {
    id: 'overview',
    title: 'Overview',
    active: true
  },
  {
    id: 'context',
    title: 'Context Object',
    active: false
  },
  {
    id: 'plugins',
    title: 'Plugin Functions',
    active: false
  },
  {
    id: 'variables',
    title: 'Variable System',
    active: false
  },
  {
    id: 'examples',
    title: 'Examples',
    active: false
  },
  {
    id: 'security',
    title: 'Security & Limitations',
    active: false
  }
])

// Plugin functions state
const pluginFunctions = ref<PluginFunction[]>([])
const functionsLoading = ref(false)
const functionsError = ref<string | null>(null)

function selectSection(sectionId: string) {
  sections.value.forEach(section => {
    section.active = section.id === sectionId
  })
}

// Fetch plugin functions from API
async function fetchPluginFunctions() {
  functionsLoading.value = true
  functionsError.value = null
  
  try {
    const response = await fetch('http://localhost:8000/api/modules/plugin-functions')
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const data = await response.json()
    pluginFunctions.value = data.functions
    
  } catch (error) {
    console.error('Failed to fetch plugin functions:', error)
    functionsError.value = error instanceof Error ? error.message : 'Failed to load plugin functions'
  } finally {
    functionsLoading.value = false
  }
}

// Group functions by category
const functionsByCategory = ref<Record<string, PluginFunction[]>>({})

function groupFunctionsByCategory() {
  const grouped: Record<string, PluginFunction[]> = {}
  
  pluginFunctions.value.forEach(func => {
    if (!grouped[func.category]) {
      grouped[func.category] = []
    }
    grouped[func.category].push(func)
  })
  
  functionsByCategory.value = grouped
}

// Format docstring to preserve line breaks and structure
function formatDocstring(docstring: string): string {
  if (!docstring) return 'No description available'
  
  return docstring
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .map(line => {
      // Convert common patterns to proper formatting
      if (line.startsWith('Args:') || line.startsWith('Arguments:')) {
        return `<strong>${line}</strong>`
      } else if (line.startsWith('Returns:') || line.startsWith('Return:')) {
        return `<strong>${line}</strong>`
      } else if (line.startsWith('Example:') || line.startsWith('Examples:')) {
        return `<strong>${line}</strong>`
      } else if (line.includes(':') && line.length < 100 && !line.includes(' ')) {
        // Likely a parameter description line
        const [param, ...desc] = line.split(':')
        if (param && desc.length > 0) {
          return `&nbsp;&nbsp;<code>${param.trim()}</code>: ${desc.join(':').trim()}`
        }
      }
      return line
    })
    .join('<br>')
}

// Load functions on mount
onMounted(async () => {
  await fetchPluginFunctions()
  groupFunctionsByCategory()
})

// Watch for changes in plugin functions
watch(pluginFunctions, () => {
  groupFunctionsByCategory()
}, { deep: true })

// Helper functions for category display
function getCategoryIcon(category: string): string {
  switch (category) {
    case 'time': return 'fa-solid fa-clock'
    case 'conversation': return 'fa-solid fa-comments'
    case 'utility': return 'fa-solid fa-tools'
    default: return 'fa-solid fa-cog'
  }
}

function getCategoryTitle(category: string): string {
  switch (category) {
    case 'time': return 'Time Functions'
    case 'conversation': return 'Conversation Functions'
    case 'utility': return 'Utility Functions'
    default: return category.charAt(0).toUpperCase() + category.slice(1) + ' Functions'
  }
}

// Go back to main app
function goBackToApp() {
  window.close() // Close current tab
  // If that doesn't work (popup blocker), navigate to home
  if (!window.closed) {
    window.location.href = '/'
  }
}
</script>

<template>
  <div class="scripting-docs-page">
    <div class="docs-header">
      <div class="header-content">
        <button class="back-to-app-btn" @click="goBackToApp" title="Back to main app">
          <i class="fa-solid fa-arrow-left"></i>
          <span>Back to App</span>
        </button>
        
        <div class="header-main">
          <div class="icon-container">
            <i class="fa-solid fa-code"></i>
          </div>
          <div class="header-text">
            <h1>Module Scripting Guide</h1>
            <p>Python scripting reference for MDCS advanced modules</p>
          </div>
        </div>
      </div>
    </div>

    <div class="docs-layout">
      <!-- Navigation Sidebar -->
      <div class="docs-nav">
        <div class="nav-header">
          <i class="fa-solid fa-list"></i>
          <span>Contents</span>
        </div>
        <div class="nav-items">
          <div 
            v-for="section in sections" 
            :key="section.id"
            :class="['nav-item', { 'active': section.active }]"
            @click="selectSection(section.id)"
          >
            {{ section.title }}
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="docs-content">
        <!-- Overview Section -->
        <div v-if="sections.find(s => s.id === 'overview')?.active" class="content-section">
          <h2>Overview</h2>
          <p>Advanced modules execute Python scripts to generate dynamic content based on conversation context. Scripts run in a sandboxed environment with access to conversation data, time functions, and AI capabilities.</p>

          <div class="info-box">
            <div class="info-header">
              <i class="fa-solid fa-lightbulb"></i>
              <span>Key Concepts</span>
            </div>
            <ul>
              <li><strong>Context Object</strong>: All functionality accessed through the <code>ctx</code> object</li>
              <li><strong>Variable System</strong>: Script variables are automatically available in templates</li>
              <li><strong>Template Substitution</strong>: Use <code>${variable}</code> syntax to insert script variables</li>
              <li><strong>Plugin Functions</strong>: ~60 built-in functions for time, conversation, AI, and utilities</li>
              <li><strong>Sandboxed Execution</strong>: RestrictedPython prevents file/network access</li>
            </ul>
          </div>

          <h3>Basic Workflow</h3>
          <ol>
            <li>Write Python script that calls plugin functions via <code>ctx</code></li>
            <li>Assign values to variables using standard Python syntax</li>
            <li>Reference variables in module content template as <code>${variable_name}</code></li>
            <li>Script executes during the module resolution pipeline</li>
            <li>Variables are automatically substituted into the final system prompt</li>
          </ol>
        </div>

        <!-- Context Object Section -->
        <div v-if="sections.find(s => s.id === 'context')?.active" class="content-section">
          <h2>Context Object (ctx)</h2>
          <p>The <code>ctx</code> object is the primary interface for all module script functionality. It provides access to conversation data, plugin functions, and variable storage.</p>

          <h3>Available Properties</h3>
          <div class="code-example">
            <div class="code-header">
              <i class="fa-solid fa-code"></i>
              <span>Context Properties</span>
            </div>
            <pre><code># Conversation identifiers
conversation_id = ctx.conversation_id  # UUID of current conversation
persona_id = ctx.persona_id            # UUID of active persona
module_id = ctx.module_id              # UUID of current module</code></pre>
          </div>

          <h3>Calling Plugin Functions</h3>
          <div class="code-example">
            <div class="code-header">
              <i class="fa-solid fa-code"></i>
              <span>Plugin Function Examples</span>
            </div>
            <pre><code># Time functions
current_time = ctx.get_current_time("%H:%M")
day = ctx.get_day_of_week()
is_business = ctx.is_business_hours()

# Conversation functions
count = ctx.get_message_count()
history = ctx.get_recent_messages(5)
summary = ctx.get_conversation_summary()

# AI functions
response = ctx.generate("Summarize this: " + text)
reflection = ctx.reflect("Analyze the conversation tone")</code></pre>
          </div>

          <h3>Creating Output Variables</h3>
          <div class="code-example">
            <div class="code-header">
              <i class="fa-solid fa-code"></i>
              <span>Variable Assignment</span>
            </div>
            <pre><code># Simple variable assignment
greeting = "Hello"
count = 42
temperature = 0.7

# Computed values
total = count * 2
message = f"Count is {count}"

# Complex values (automatically converted to strings)
summary = {
    "messages": count,
    "time": current_time
}</code></pre>
          </div>

          <div class="info-box warning">
            <div class="info-header">
              <i class="fa-solid fa-exclamation-triangle"></i>
              <span>Important</span>
            </div>
            <p>All plugin functions MUST be accessed through the <code>ctx</code> object. Direct function calls (e.g., <code>get_current_time()</code>) will fail. Always use <code>ctx.function_name()</code> syntax.</p>
          </div>
        </div>

        <!-- Plugin Functions Section -->
        <div v-if="sections.find(s => s.id === 'plugins')?.active" class="content-section">
          <h2>Plugin Functions</h2>
          <p>Built-in functions available through the <code>ctx</code> object:</p>

          <!-- Loading State -->
          <div v-if="functionsLoading" class="loading-state">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <span>Loading plugin functions...</span>
          </div>

          <!-- Error State -->
          <div v-else-if="functionsError" class="error-state">
            <i class="fa-solid fa-exclamation-triangle"></i>
            <span>Error loading functions: {{ functionsError }}</span>
            <button @click="fetchPluginFunctions" class="retry-btn">
              <i class="fa-solid fa-redo"></i>
              Retry
            </button>
          </div>

          <!-- Dynamic Plugin Categories -->
          <div v-else>
            <div class="functions-summary">
              <p><strong>{{ pluginFunctions.length }}</strong> functions available across {{ Object.keys(functionsByCategory).length }} categories</p>
            </div>

            <div v-for="(functions, category) in functionsByCategory" :key="category" class="plugin-category">
              <h3>
                <i :class="getCategoryIcon(category)"></i>
                {{ getCategoryTitle(category) }}
              </h3>
              <div class="function-grid">
                <div v-for="func in functions" :key="func.name" class="function-item">
                  <div class="function-signature">
                    <code>{{ func.signature }}</code>
                  </div>
                  <div class="function-description" v-html="formatDocstring(func.docstring)"></div>
                  
                  <!-- Parameters -->
                  <div v-if="func.parameters.length > 0" class="function-parameters">
                    <h5>Parameters:</h5>
                    <div class="parameter-list">
                      <div v-for="param in func.parameters" :key="param.name" class="parameter-item">
                        <code class="param-name">{{ param.name }}</code>
                        <span class="param-type">{{ param.type }}</span>
                        <span v-if="!param.required" class="param-optional">(optional)</span>
                        <span v-if="param.default" class="param-default">= {{ param.default }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Variable System Section -->
        <div v-if="sections.find(s => s.id === 'variables')?.active" class="content-section">
          <h2>Variable System</h2>
          <p>Variables created in your script are automatically available in the module content template. Simply assign values using normal Python syntax, then reference them using <code>${variable_name}</code>.</p>

          <div class="variable-example">
            <div class="example-part">
              <h4>Script:</h4>
              <div class="code-example">
                <pre><code># Get data from plugins
time_of_day = ctx.get_current_time("%H:%M")
hour = int(time_of_day.split(':')[0])

# Create variables
if hour < 12:
    greeting = "Good morning"
else:
    greeting = "Good afternoon"

persona_name = "AVA"</code></pre>
              </div>
            </div>

            <div class="example-part">
              <h4>Content Template:</h4>
              <div class="code-example">
                <pre><code>${greeting}! I'm ${persona_name}.
Current time is ${time_of_day}.</code></pre>
              </div>
            </div>

            <div class="example-part">
              <h4>Resolved Output:</h4>
              <div class="resolved-example">
                Good afternoon! I'm AVA.<br>
                Current time is 14:30.
              </div>
            </div>
          </div>

          <div class="info-box">
            <div class="info-header">
              <i class="fa-solid fa-info-circle"></i>
              <span>Variable Rules</span>
            </div>
            <ul>
              <li>Variables are created with standard Python assignment (e.g., <code>greeting = "Hello"</code>)</li>
              <li>Variable names must be valid Python identifiers (letters, numbers, underscores)</li>
              <li>Reference variables in templates using <code>${variable_name}</code> syntax</li>
              <li>Values are automatically converted to strings when substituted</li>
              <li>Undefined variables remain as <code>${variable_name}</code> in output</li>
              <li>Variables are scoped to the current module execution only</li>
            </ul>
          </div>
        </div>

        <!-- Examples Section -->
        <div v-if="sections.find(s => s.id === 'examples')?.active" class="content-section">
          <h2>Examples</h2>
          
          <div class="example-container">
            <h3>1. Dynamic Greeting Module</h3>
            <div class="example-grid">
              <div class="example-script">
                <h4>Script:</h4>
                <div class="code-example">
                  <pre><code>current_hour = int(ctx.get_current_time("%H"))
message_count = ctx.get_message_count()

# Determine greeting based on time
if current_hour < 12:
    time_greeting = "Good morning"
elif current_hour < 17:
    time_greeting = "Good afternoon"
else:
    time_greeting = "Good evening"

# Determine context based on conversation length
if message_count == 0:
    context = "It's great to meet you!"
elif message_count < 10:
    context = "Nice to chat with you again."
else:
    context = "We've had quite a conversation!"</code></pre>
                </div>
              </div>
              <div class="example-content">
                <h4>Content:</h4>
                <div class="code-example">
                  <pre><code>${time_greeting}! ${context}</code></pre>
                </div>
              </div>
            </div>
          </div>

          <div class="example-container">
            <h3>2. Conversation Context Module</h3>
            <div class="example-grid">
              <div class="example-script">
                <h4>Script:</h4>
                <div class="code-example">
                  <pre><code>count = ctx.get_message_count()
recent = ctx.get_recent_messages(5)

# Determine conversation status
if count > 20:
    status = "We've had an extensive discussion"
elif count > 5:
    status = "We've been chatting for a bit"
else:
    status = "We're just getting started"

# Format recent history
history_text = "\n".join([
    f"- {msg['role']}: {msg['content'][:50]}..."
    for msg in recent
])</code></pre>
                </div>
              </div>
              <div class="example-content">
                <h4>Content:</h4>
                <div class="code-example">
                  <pre><code>${status}

Recent context:
${history_text}</code></pre>
                </div>
              </div>
            </div>
          </div>

          <div class="example-container">
            <h3>3. AI Self-Reflection Module</h3>
            <div class="example-grid">
              <div class="example-script">
                <h4>Script:</h4>
                <div class="code-example">
                  <pre><code># Use AI to analyze conversation
analysis = ctx.reflect(
    "Analyze the conversation tone and user intent "
    "in 1-2 sentences"
)</code></pre>
                </div>
              </div>
              <div class="example-content">
                <h4>Content:</h4>
                <div class="code-example">
                  <pre><code>Conversation analysis:
${analysis}</code></pre>
                </div>
                <h4>Note:</h4>
                <p style="font-size: 0.9em; opacity: 0.8; margin-top: 8px;">
                  This module requires AI inference and will execute in Stage 2 (pre-response AI).
                  The <code>ctx.reflect()</code> function uses the current resolved system prompt.
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Security Section -->
        <div v-if="sections.find(s => s.id === 'security')?.active" class="content-section">
          <h2>Security & Limitations</h2>
          
          <div class="security-grid">
            <div class="security-item allowed">
              <div class="security-header">
                <i class="fa-solid fa-check-circle"></i>
                <span>Allowed Operations</span>
              </div>
              <ul>
                <li>Basic Python syntax (variables, conditions, loops)</li>
                <li>Math operations and built-in functions</li>
                <li>String manipulation and formatting</li>
                <li>List, dict, tuple, set operations</li>
                <li>Allowed modules: datetime, math, json, re, uuid, random, time</li>
                <li>Plugin function access via <code>ctx</code></li>
              </ul>
            </div>

            <div class="security-item restricted">
              <div class="security-header">
                <i class="fa-solid fa-ban"></i>
                <span>Restricted Operations</span>
              </div>
              <ul>
                <li>File system access (open, read, write files)</li>
                <li>Network operations (HTTP requests, sockets)</li>
                <li>Process execution (subprocess, os commands)</li>
                <li>Import of arbitrary modules</li>
                <li>Access to Python internals (__import__, eval, exec)</li>
                <li>Global variable modification</li>
              </ul>
            </div>
          </div>

          <div class="info-box warning">
            <div class="info-header">
              <i class="fa-solid fa-shield-alt"></i>
              <span>Execution Limits</span>
            </div>
            <ul>
              <li><strong>Timeout:</strong> Scripts must complete within 30 seconds (configurable per module)</li>
              <li><strong>AI Operations:</strong> <code>ctx.reflect()</code> and <code>ctx.generate()</code> can use up to 60 seconds</li>
              <li><strong>Memory:</strong> Limited memory allocation enforced by RestrictedPython</li>
              <li><strong>Recursion:</strong> Maximum depth enforced by Python runtime</li>
              <li><strong>Reflection Depth:</strong> Maximum 3 levels of nested <code>ctx.reflect()</code> calls to prevent infinite loops</li>
            </ul>
          </div>

          <div class="best-practices">
            <h3>Best Practices</h3>
            <ul>
              <li>Keep scripts simple and focused on single tasks</li>
              <li>Test scripts using the "Test Script" button before saving</li>
              <li>Handle potential errors gracefully with try/except blocks</li>
              <li>Use descriptive variable names</li>
              <li>Comment complex logic for maintainability</li>
              <li>Avoid expensive operations in frequently-triggered modules</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Base page styles */
.scripting-docs-page {
  width: 100vw;
  height: 100vh;
  background: var(--bg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.docs-header {
  background: linear-gradient(135deg, var(--surface) 0%, var(--secondary) 100%);
  border-bottom: 2px solid var(--border);
  padding: 20px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.back-to-app-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.9em;
}

.back-to-app-btn:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
  transform: translateY(-1px);
}

.header-main {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.icon-container {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, var(--accent) 0%, #ff4757 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
  box-shadow: 0 4px 12px rgba(255, 0, 110, 0.3);
}

.header-text h1 {
  color: var(--fg);
  font-size: 2em;
  font-weight: 700;
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.header-text p {
  color: var(--fg);
  opacity: 0.7;
  margin: 0;
  font-size: 1.1em;
}

.docs-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.docs-nav {
  width: 280px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 20px 0;
  overflow-y: auto;
}

.nav-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px 16px 20px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  margin-bottom: 16px;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.9em;
}

.nav-items {
  padding: 0 20px;
}

.nav-item {
  padding: 12px 16px;
  margin-bottom: 4px;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.2s ease;
  color: var(--fg);
  font-weight: 500;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: rgba(0, 212, 255, 0.1);
  border-left-color: rgba(0, 212, 255, 0.5);
}

.nav-item.active {
  background: rgba(255, 0, 110, 0.1);
  border-left-color: var(--accent);
  color: var(--accent);
  font-weight: 600;
}

.docs-content {
  flex: 1;
  padding: 32px 40px;
  overflow-y: auto;
  max-width: 1000px;
  margin: 0 auto;
}

.content-section {
  width: 100%;
}

.content-section h2 {
  color: var(--fg);
  font-size: 2em;
  font-weight: 700;
  margin: 0 0 20px 0;
  border-bottom: 2px solid var(--accent);
  padding-bottom: 12px;
}

.content-section h3 {
  color: var(--accent);
  font-size: 1.4em;
  font-weight: 600;
  margin: 24px 0 16px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.content-section h4 {
  color: var(--fg);
  font-size: 1.1em;
  font-weight: 600;
  margin: 16px 0 8px 0;
}

.content-section p {
  color: var(--fg);
  line-height: 1.6;
  margin-bottom: 16px;
  opacity: 0.9;
}

.content-section ol, .content-section ul {
  color: var(--fg);
  line-height: 1.6;
  margin-bottom: 16px;
  padding-left: 24px;
}

.content-section li {
  margin-bottom: 8px;
}

.info-box {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 4px;
  padding: 16px;
  margin: 20px 0;
}

.info-box.warning {
  background: rgba(255, 193, 7, 0.05);
  border-color: rgba(255, 193, 7, 0.3);
}

.info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.9em;
}

.info-box.warning .info-header {
  color: #ffc107;
}

.code-example {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 4px;
  margin: 16px 0;
  overflow: hidden;
}

.code-header {
  background: rgba(0, 212, 255, 0.1);
  padding: 8px 12px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8em;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.code-example pre {
  padding: 16px;
  margin: 0;
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
  line-height: 1.4;
  color: var(--fg);
  overflow-x: auto;
}

.code-example code {
  color: var(--fg);
  font-family: 'Fira Code', monospace;
}

.plugin-category {
  margin: 32px 0;
}

.function-grid {
  display: grid;
  gap: 16px;
  margin: 16px 0;
}

.function-item {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 4px;
  padding: 16px;
}

.function-signature {
  font-family: 'Fira Code', monospace;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 0.9em;
}

.function-description {
  color: var(--fg);
  opacity: 0.8;
  font-size: 0.9em;
  margin-bottom: 8px;
  line-height: 1.5;
}

.function-description strong {
  color: var(--accent);
  font-weight: 600;
  display: block;
  margin-top: 8px;
  margin-bottom: 4px;
}

.function-description code {
  background: rgba(0, 212, 255, 0.1);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  color: var(--accent);
}

.variable-example {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 4px;
  padding: 20px;
  margin: 20px 0;
}

.example-part {
  margin-bottom: 20px;
}

.resolved-example {
  background: rgba(0, 255, 65, 0.05);
  border: 1px solid rgba(0, 255, 65, 0.2);
  border-radius: 4px;
  padding: 16px;
  color: #00ff41;
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
  line-height: 1.4;
}

.example-container {
  background: rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 4px;
  padding: 24px;
  margin: 24px 0;
}

.example-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 16px;
}

.security-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin: 24px 0;
}

.security-item {
  border-radius: 4px;
  padding: 20px;
  border: 1px solid;
}

.security-item.allowed {
  background: rgba(0, 255, 65, 0.05);
  border-color: rgba(0, 255, 65, 0.2);
}

.security-item.restricted {
  background: rgba(255, 71, 87, 0.05);
  border-color: rgba(255, 71, 87, 0.2);
}

.security-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.9em;
}

.security-item.allowed .security-header {
  color: #00ff41;
}

.security-item.restricted .security-header {
  color: #ff4757;
}

.best-practices {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 4px;
  padding: 20px;
  margin: 24px 0;
}

.best-practices h3 {
  color: var(--accent);
  margin-top: 0;
}

/* Dynamic plugin functions styles */
.loading-state, .error-state {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 4px;
  margin: 20px 0;
}

.loading-state {
  color: var(--fg);
  opacity: 0.8;
}

.loading-state i {
  color: var(--accent);
  font-size: 1.2em;
}

.error-state {
  color: #ff4757;
  border-color: rgba(255, 71, 87, 0.3);
  background: rgba(255, 71, 87, 0.05);
}

.retry-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--accent);
  border: none;
  color: white;
  border-radius: 2px;
  font-size: 0.8em;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retry-btn:hover {
  background: #ff4757;
  transform: translateY(-1px);
}

.functions-summary {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 4px;
  padding: 16px;
  margin: 20px 0;
  text-align: center;
}

.functions-summary p {
  margin: 0;
  color: var(--accent);
  font-weight: 600;
}

.function-parameters {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.function-parameters h5 {
  color: var(--accent);
  font-size: 0.8em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 8px 0;
}

.parameter-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.parameter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8em;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

.param-name {
  color: var(--accent);
  font-family: 'Fira Code', monospace;
  font-weight: 600;
}

.param-type {
  color: #00ff41;
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
}

.param-optional {
  color: var(--fg);
  opacity: 0.6;
  font-style: italic;
  font-size: 0.9em;
}

.param-default {
  color: #ffa500;
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
}

/* Responsive Design */
@media (max-width: 1024px) {
  .docs-layout {
    flex-direction: column;
  }
  
  .docs-nav {
    width: 100%;
    max-height: 200px;
  }
  
  .nav-items {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 0 20px;
  }
  
  .nav-item {
    margin: 0;
    white-space: nowrap;
  }
  
  .example-grid {
    grid-template-columns: 1fr;
  }
  
  .security-grid {
    grid-template-columns: 1fr;
  }
  
  .header-content {
    flex-direction: column;
    gap: 16px;
  }
  
  .back-to-app-btn {
    align-self: flex-start;
  }
}
</style>