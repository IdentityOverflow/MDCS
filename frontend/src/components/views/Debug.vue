<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { usePersonas } from '@/composables/usePersonas'
import { useApiConfig } from '@/composables/apiConfig'
import type { Persona } from '@/types'

// State
const selectedPersona = ref<Persona | null>(null)
const templateResolution = ref<{
  resolved_template: string
  warnings: Array<{ module_name: string; warning_type: string; message: string }>
  resolved_modules: string[]
} | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// Composables
const { personas, fetchPersonas } = usePersonas()
const apiConfig = useApiConfig()

// Load personas on mount
onMounted(async () => {
  await fetchPersonas()
})

// Computed
const activePersonas = computed(() => 
  personas.value.filter(persona => persona.is_active)
)

// Resolve template for selected persona
async function resolveTemplate() {
  if (!selectedPersona.value?.template) {
    templateResolution.value = null
    return
  }

  loading.value = true
  error.value = null

  try {
    const response = await apiConfig.apiRequest('/api/templates/resolve', {
      method: 'POST',
      body: JSON.stringify({
        template: selectedPersona.value.template
      })
    })

    if (!response.ok) {
      const errorData = await response.text()
      throw new Error(`HTTP ${response.status}: ${errorData}`)
    }

    templateResolution.value = await response.json()
  } catch (err) {
    console.error('Failed to resolve template:', err)
    error.value = err instanceof Error ? err.message : 'Failed to resolve template'
    templateResolution.value = null
  } finally {
    loading.value = false
  }
}

// Handle persona selection
async function onPersonaSelect(persona: Persona) {
  selectedPersona.value = persona
  await resolveTemplate()
}

// Format warning type for display
function formatWarningType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// Get icon for warning type
function getWarningIcon(type: string): string {
  switch (type) {
    case 'missing_module':
      return 'fa-exclamation-triangle'
    case 'circular_dependency':
      return 'fa-circle-exclamation'
    case 'invalid_module_name':
      return 'fa-times-circle'
    case 'resolution_error':
      return 'fa-exclamation-circle'
    default:
      return 'fa-info-circle'
  }
}

// Get CSS class for warning type
function getWarningClass(type: string): string {
  switch (type) {
    case 'missing_module':
    case 'circular_dependency':
    case 'invalid_module_name':
    case 'resolution_error':
      return 'error'
    default:
      return 'info'
  }
}
</script>

<template>
  <div class="debug-view">
    <div class="debug-header">
      <h2 class="debug-title">
        <i class="fa-solid fa-bug"></i>
        Debug Console
      </h2>
      <p class="debug-subtitle">
        Template Resolution & System Prompt Analysis
      </p>
    </div>

    <div class="debug-content">
      <!-- Persona Selection -->
      <div class="debug-section">
        <h3 class="section-title">
          <i class="fa-solid fa-user-tie"></i>
          Select Persona
        </h3>
        <div class="persona-grid">
          <button
            v-for="persona in activePersonas"
            :key="persona.id"
            :class="[
              'persona-card', 
              { 'selected': selectedPersona?.id === persona.id }
            ]"
            @click="onPersonaSelect(persona)"
          >
            <div class="persona-info">
              <div class="persona-name">{{ persona.name }}</div>
              <div v-if="persona.description" class="persona-description">
                {{ persona.description }}
              </div>
            </div>
          </button>
        </div>
        <div v-if="activePersonas.length === 0" class="no-personas">
          No active personas found. Create a persona first.
        </div>
      </div>

      <!-- Template Analysis -->
      <div v-if="selectedPersona" class="debug-section">
        <h3 class="section-title">
          <i class="fa-solid fa-file-code"></i>
          Template Analysis
        </h3>
        
        <!-- Original Template -->
        <div class="template-box">
          <div class="template-header">
            <h4>Original Template</h4>
            <span class="template-meta">{{ selectedPersona.template?.length || 0 }} characters</span>
          </div>
          <pre class="template-content original">{{ selectedPersona.template || '(Empty template)' }}</pre>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <i class="fa-solid fa-spinner fa-spin"></i>
          <span>Resolving template...</span>
        </div>

        <!-- Error State -->
        <div v-if="error" class="error-state">
          <i class="fa-solid fa-exclamation-triangle"></i>
          <span>{{ error }}</span>
        </div>

        <!-- Resolution Results -->
        <div v-if="templateResolution" class="resolution-results">
          <!-- Resolved Template -->
          <div class="template-box">
            <div class="template-header">
              <h4>Resolved System Prompt</h4>
              <span class="template-meta">{{ templateResolution.resolved_template.length }} characters</span>
            </div>
            <pre class="template-content resolved">{{ templateResolution.resolved_template }}</pre>
          </div>

          <!-- Resolved Modules -->
          <div v-if="templateResolution.resolved_modules.length > 0" class="modules-section">
            <h4 class="modules-title">
              <i class="fa-solid fa-puzzle-piece"></i>
              Resolved Modules ({{ templateResolution.resolved_modules.length }})
            </h4>
            <div class="modules-list">
              <span
                v-for="moduleName in templateResolution.resolved_modules"
                :key="moduleName"
                class="module-tag"
              >
                @{{ moduleName }}
              </span>
            </div>
          </div>

          <!-- Warnings -->
          <div v-if="templateResolution.warnings.length > 0" class="warnings-section">
            <h4 class="warnings-title">
              <i class="fa-solid fa-exclamation-triangle"></i>
              Resolution Warnings ({{ templateResolution.warnings.length }})
            </h4>
            <div class="warnings-list">
              <div
                v-for="warning in templateResolution.warnings"
                :key="`${warning.module_name}-${warning.message}`"
                :class="['warning-item', getWarningClass(warning.warning_type)]"
              >
                <i :class="['fa-solid', getWarningIcon(warning.warning_type)]"></i>
                <div class="warning-content">
                  <div class="warning-header">
                    <span class="warning-type">{{ formatWarningType(warning.warning_type) }}</span>
                    <span v-if="warning.module_name" class="warning-module">@{{ warning.module_name }}</span>
                  </div>
                  <div class="warning-message">{{ warning.message }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Success State -->
          <div v-if="templateResolution.warnings.length === 0" class="success-state">
            <i class="fa-solid fa-check-circle"></i>
            <span>Template resolved successfully with no warnings!</span>
          </div>
        </div>
      </div>

      <!-- Instructions -->
      <div v-if="!selectedPersona" class="instructions">
        <div class="instructions-content">
          <i class="fa-solid fa-lightbulb"></i>
          <h3>Template Resolution Debug Tool</h3>
          <p>
            This debug console allows you to inspect how persona templates are resolved into system prompts.
            Select a persona above to see:
          </p>
          <ul>
            <li>Original template with @module references</li>
            <li>Fully resolved system prompt</li>
            <li>List of modules that were resolved</li>
            <li>Any warnings or errors during resolution</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';

.debug-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--fg);
}

.debug-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(0, 212, 255, 0.05);
}

.debug-title {
  margin: 0 0 4px 0;
  color: var(--accent);
  font-size: 1.2em;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.debug-subtitle {
  margin: 0;
  color: var(--fg);
  opacity: 0.7;
  font-size: 0.85em;
}

.debug-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.debug-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  color: var(--accent);
  font-size: 1em;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Persona Selection */
.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
}

.persona-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 12px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.persona-card:hover {
  border-color: var(--accent);
  background: rgba(0, 212, 255, 0.05);
}

.persona-card.selected {
  border-color: var(--accent);
  background: rgba(0, 212, 255, 0.1);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.2);
}

.persona-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.persona-name {
  font-weight: 600;
  color: var(--fg);
}

.persona-description {
  font-size: 0.8em;
  color: var(--fg);
  opacity: 0.7;
  line-height: 1.3;
}

.no-personas {
  text-align: center;
  padding: 24px;
  color: var(--fg);
  opacity: 0.6;
  font-style: italic;
}

/* Template Boxes */
.template-box {
  border: 1px solid var(--border);
  border-radius: 2px;
  overflow: hidden;
}

.template-header {
  background: rgba(0, 212, 255, 0.1);
  padding: 8px 12px;
  display: flex;
  justify-content: between;
  align-items: center;
  border-bottom: 1px solid var(--border);
}

.template-header h4 {
  margin: 0;
  color: var(--accent);
  font-size: 0.85em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex: 1;
}

.template-meta {
  font-size: 0.75em;
  color: var(--fg);
  opacity: 0.6;
  font-family: monospace;
}

.template-content {
  background: var(--bg-2);
  padding: 12px;
  margin: 0;
  font-family: 'Fira Code', monospace;
  font-size: 0.8em;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--fg);
  max-height: 300px;
  overflow-y: auto;
}

.template-content.original {
  color: var(--fg);
  opacity: 0.8;
}

.template-content.resolved {
  color: var(--accent);
  background: rgba(0, 212, 255, 0.03);
}

/* Loading and Error States */
.loading-state,
.error-state,
.success-state {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 2px;
  font-size: 0.9em;
}

.loading-state {
  background: rgba(0, 212, 255, 0.1);
  color: var(--accent);
}

.error-state {
  background: rgba(255, 71, 87, 0.1);
  color: #ff4757;
}

.success-state {
  background: rgba(46, 213, 115, 0.1);
  color: #2ed573;
}

/* Modules Section */
.modules-section {
  margin-top: 16px;
}

.modules-title {
  color: var(--accent);
  font-size: 0.85em;
  font-weight: 600;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.modules-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.module-tag {
  background: rgba(0, 212, 255, 0.2);
  color: var(--accent);
  padding: 4px 8px;
  border-radius: 2px;
  font-size: 0.75em;
  font-family: 'Fira Code', monospace;
  font-weight: 600;
}

/* Warnings Section */
.warnings-section {
  margin-top: 16px;
}

.warnings-title {
  color: #ffa726;
  font-size: 0.85em;
  font-weight: 600;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.warnings-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.warning-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 2px;
  border-left: 3px solid;
}

.warning-item.error {
  background: rgba(255, 71, 87, 0.1);
  border-left-color: #ff4757;
  color: #ff4757;
}

.warning-item.info {
  background: rgba(0, 212, 255, 0.1);
  border-left-color: var(--accent);
  color: var(--accent);
}

.warning-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.warning-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8em;
}

.warning-type {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.warning-module {
  font-family: 'Fira Code', monospace;
  background: rgba(0, 0, 0, 0.2);
  padding: 2px 4px;
  border-radius: 1px;
}

.warning-message {
  font-size: 0.85em;
  line-height: 1.3;
  opacity: 0.9;
}

/* Instructions */
.instructions {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.instructions-content {
  text-align: center;
  max-width: 500px;
  padding: 24px;
}

.instructions-content i {
  font-size: 3em;
  color: var(--accent);
  margin-bottom: 16px;
  display: block;
}

.instructions-content h3 {
  color: var(--accent);
  margin: 0 0 12px 0;
  font-size: 1.1em;
}

.instructions-content p {
  color: var(--fg);
  opacity: 0.8;
  line-height: 1.5;
  margin: 0 0 16px 0;
}

.instructions-content ul {
  text-align: left;
  color: var(--fg);
  opacity: 0.7;
  line-height: 1.4;
}
</style>