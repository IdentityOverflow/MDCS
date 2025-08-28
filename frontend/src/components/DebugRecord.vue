<script setup lang="ts">
import { ref, computed } from 'vue'
import type { DebugRecord } from '@/composables/useDebug'

const props = defineProps<{
  record: DebugRecord
}>()

// Component state
const isExpanded = ref(false)
const activeTab = ref<'request' | 'response'>('request')

// Computed properties
const formattedTimestamp = computed(() => {
  return new Date(props.record.timestamp).toLocaleString()
})

const responseTimeMs = computed(() => {
  return Math.round(props.record.response_time * 1000)
})

const systemPromptPreview = computed(() => {
  // First try resolved_system_prompt (from backend response)
  if (props.record.resolved_system_prompt) {
    const prompt = props.record.resolved_system_prompt
    if (prompt.length <= 100) return prompt
    return prompt.substring(0, 100) + '...'
  }
  
  // Then try to find system prompt in actual provider request format
  const request = props.record.request as any
  if (request && request.messages) {
    // Look for system message in messages array (Ollama/OpenAI format)
    const systemMessage = request.messages.find((msg: any) => msg.role === 'system')
    if (systemMessage && systemMessage.content) {
      const prompt = systemMessage.content
      if (prompt.length <= 100) return prompt
      return prompt.substring(0, 100) + '...'
    }
  }
  
  // Fallback to direct system_prompt field (legacy format)
  if (request && request.system_prompt) {
    const prompt = request.system_prompt
    if (prompt.length <= 100) return prompt
    return prompt.substring(0, 100) + '...'
  }
  
  return 'No system prompt'
})

const fullSystemPrompt = computed(() => {
  // First try resolved_system_prompt (from backend response)
  if (props.record.resolved_system_prompt) {
    return props.record.resolved_system_prompt
  }
  
  // Then try to find system prompt in actual provider request format
  const request = props.record.request as any
  if (request && request.messages) {
    // Look for system message in messages array (Ollama/OpenAI format)
    const systemMessage = request.messages.find((msg: any) => msg.role === 'system')
    if (systemMessage && systemMessage.content) {
      return systemMessage.content
    }
  }
  
  // Fallback to direct system_prompt field (legacy format)
  if (request && request.system_prompt) {
    return request.system_prompt
  }
  
  return 'No system prompt'
})

// Toggle expanded state
const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}

// Format JSON for display
const formatJson = (obj: any): string => {
  return JSON.stringify(obj, null, 2)
}

// Get request/response data for display
const getRequestData = computed(() => {
  // Always show the actual provider request (what gets sent to Ollama/OpenAI)
  return props.record.request
})

const getResponseData = computed(() => {
  // Always show raw response data
  return props.record.response
})
</script>

<template>
  <div class="debug-record">
    <!-- Record Header -->
    <div class="record-header" @click="toggleExpanded">
      <div class="record-title">
        <i :class="['fa-solid', isExpanded ? 'fa-chevron-down' : 'fa-chevron-right']"></i>
        <span class="timestamp">{{ formattedTimestamp }}</span>
      </div>
      
      <div class="record-meta">
        <span v-if="record.persona_name" class="persona">{{ record.persona_name }}</span>
        <span class="provider">{{ record.provider }}</span>
        <span class="model">{{ record.model }}</span>
        <span class="response-time">{{ responseTimeMs }}ms</span>
      </div>
    </div>

    <!-- Expanded Content -->
    <div v-if="isExpanded" class="record-content">
      <!-- System Prompt Highlight -->
      <div class="system-prompt-section">
        <h4>
          <i class="fa-solid fa-terminal"></i>
          System Prompt
        </h4>
        <div class="system-prompt">
          <pre>{{ fullSystemPrompt }}</pre>
        </div>
      </div>

      <!-- No controls needed - always show provider format -->

      <!-- Tabs -->
      <div class="record-tabs">
        <div class="tab-headers">
          <button 
            :class="['tab-header', { active: activeTab === 'request' }]"
            @click="activeTab = 'request'"
          >
            <i class="fa-solid fa-arrow-right"></i>
            Request
          </button>
          <button 
            :class="['tab-header', { active: activeTab === 'response' }]"
            @click="activeTab = 'response'"
          >
            <i class="fa-solid fa-arrow-left"></i>
            Response
          </button>
        </div>

        <!-- Request Tab -->
        <div v-if="activeTab === 'request'" class="tab-content">
          <div class="raw-content">
            <pre>{{ formatJson(getRequestData) }}</pre>
          </div>
        </div>

        <!-- Response Tab -->
        <div v-if="activeTab === 'response'" class="tab-content">
          <div class="raw-content">
            <pre>{{ formatJson(getResponseData) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.debug-record {
  border: 1px solid var(--border);
  border-radius: 4px;
  margin-bottom: 12px;
  background: var(--surface);
}

.record-header {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background-color 0.2s ease;
}

.record-header:hover {
  background: rgba(0, 212, 255, 0.05);
}

.record-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.record-title i {
  color: var(--accent);
  font-size: 0.8em;
}

.timestamp {
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
  color: var(--fg);
  font-weight: 600;
}

.record-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.8em;
}

.persona {
  color: var(--accent);
  font-weight: 600;
}

.provider {
  color: var(--fg);
  opacity: 0.8;
}

.model {
  color: var(--fg);
  opacity: 0.7;
  font-family: 'Fira Code', monospace;
}

.response-time {
  color: #2ed573;
  font-family: 'Fira Code', monospace;
  font-weight: 600;
}

.record-content {
  border-top: 1px solid var(--border);
  padding: 16px;
}

.system-prompt-section {
  margin-bottom: 20px;
}

.system-prompt-section h4 {
  color: var(--accent);
  font-size: 0.9em;
  font-weight: 600;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.system-prompt {
  background: rgba(0, 212, 255, 0.03);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 4px;
  padding: 12px;
}

.system-prompt pre {
  margin: 0;
  color: var(--accent);
  font-family: 'Fira Code', monospace;
  font-size: 0.8em;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Tab styling */

.tab-headers {
  display: flex;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}

.tab-header {
  background: none;
  border: none;
  padding: 8px 16px;
  color: var(--fg);
  opacity: 0.6;
  cursor: pointer;
  font-size: 0.85em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.tab-header:hover {
  opacity: 0.8;
  background: rgba(0, 212, 255, 0.05);
}

.tab-header.active {
  opacity: 1;
  color: var(--accent);
  border-bottom: 2px solid var(--accent);
}

.tab-content {
  min-height: 200px;
}

/* Raw content is now the only content display */

.json-content,
.raw-content pre {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px;
  margin: 0;
  color: var(--fg);
  font-family: 'Fira Code', monospace;
  font-size: 0.75em;
  line-height: 1.3;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}

.raw-content {
  margin-top: 8px;
}
</style>