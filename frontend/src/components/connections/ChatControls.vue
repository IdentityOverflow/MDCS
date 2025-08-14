<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLocalStorage, useNotification } from '@/composables/storage'

// Default chat controls based on connections.md spec
const defaultChatControls = {
  system_or_instructions: '',
  temperature: 0.7,
  top_p: 1.0,
  max_tokens: 1024,
  presence_penalty: 0.0,
  frequency_penalty: 0.0,
  seed: null,
  stop: [],
  json_mode: 'off',
  tools: [],
  tool_choice: 'auto',
  stream: true,
  
  // Ollama-specific controls
  ollama_top_k: 40,
  ollama_repeat_penalty: 1.1,
  ollama_mirostat: 0,
  ollama_num_ctx: 8192,
  
  // OpenAI reasoning model controls
  reasoning_effort: 'low',
  verbosity: 'medium'
}

// Storage management
const { data: chatControls, save: saveToStorage, load: loadFromStorage } = useLocalStorage({
  key: 'chat-controls',
  defaultValue: defaultChatControls,
  validate: (value) => {
    return value && typeof value.temperature === 'number' && typeof value.top_p === 'number'
  }
})

// Notification system
const notification = useNotification()

// Load data on component mount
onMounted(() => {
  loadFromStorage()
})

// State for managing stop sequences input
const newStopSequence = ref('')

function addStopSequence() {
  if (newStopSequence.value.trim()) {
    chatControls.value.stop.push(newStopSequence.value.trim())
    newStopSequence.value = ''
  }
}

function removeStopSequence(index: number) {
  chatControls.value.stop.splice(index, 1)
}

function saveControls() {
  const success = saveToStorage()
  if (success) {
    notification.showSuccess('Chat controls saved successfully')
  } else {
    notification.showError('Failed to save chat controls')
  }
}

function resetToDefaults() {
  Object.assign(chatControls.value, structuredClone(defaultChatControls))
  notification.showSuccess('Reset to default values')
}
</script>

<template>
  <form class="form" @submit.prevent="saveControls">
    <!-- System / Instructions -->
    <div class="form-group">
      <label for="system-instructions">System / Instructions</label>
      <textarea 
        id="system-instructions"
        v-model="chatControls.system_or_instructions" 
        class="form-textarea"
        rows="4"
        placeholder="System prompt for Chat Completions; 'instructions' for Responses API"
      ></textarea>
      <small class="form-hint">System prompt for Chat Completions; 'instructions' for Responses API</small>
    </div>

    <!-- Temperature -->
    <div class="form-group">
      <label for="temperature">Temperature</label>
      <div class="slider-group">
        <input 
          id="temperature"
          v-model.number="chatControls.temperature" 
          type="range" 
          min="0.0" 
          max="2.0" 
          step="0.1"
          class="form-slider"
        />
        <span class="slider-value">{{ chatControls.temperature }}</span>
      </div>
      <small class="form-hint">Higher = more diverse/creative; lower = more deterministic</small>
    </div>

    <!-- Top-p -->
    <div class="form-group">
      <label for="top-p">Top-p</label>
      <div class="slider-group">
        <input 
          id="top-p"
          v-model.number="chatControls.top_p" 
          type="range" 
          min="0.0" 
          max="1.0" 
          step="0.01"
          class="form-slider"
        />
        <span class="slider-value">{{ chatControls.top_p.toFixed(2) }}</span>
      </div>
      <small class="form-hint">Nucleus sampling parameter</small>
    </div>

    <!-- Max Output Tokens -->
    <div class="form-group">
      <label for="max-tokens">Max Output Tokens</label>
      <div class="slider-group">
        <input 
          id="max-tokens"
          v-model.number="chatControls.max_tokens" 
          type="range" 
          min="1" 
          max="8192" 
          step="1"
          class="form-slider"
        />
        <span class="slider-value">{{ chatControls.max_tokens }}</span>
      </div>
      <small class="form-hint">Upper bound on tokens the model may generate</small>
    </div>

    <!-- Presence Penalty -->
    <div class="form-group">
      <label for="presence-penalty">Presence Penalty</label>
      <div class="slider-group">
        <input 
          id="presence-penalty"
          v-model.number="chatControls.presence_penalty" 
          type="range" 
          min="-2.0" 
          max="2.0" 
          step="0.1"
          class="form-slider"
        />
        <span class="slider-value">{{ chatControls.presence_penalty.toFixed(1) }}</span>
      </div>
      <small class="form-hint">Penalize introducing tokens simply because they already appeared</small>
    </div>

    <!-- Frequency Penalty -->
    <div class="form-group">
      <label for="frequency-penalty">Frequency Penalty</label>
      <div class="slider-group">
        <input 
          id="frequency-penalty"
          v-model.number="chatControls.frequency_penalty" 
          type="range" 
          min="-2.0" 
          max="2.0" 
          step="0.1"
          class="form-slider"
        />
        <span class="slider-value">{{ chatControls.frequency_penalty.toFixed(1) }}</span>
      </div>
      <small class="form-hint">Penalize token repetition frequency</small>
    </div>

    <!-- Seed -->
    <div class="form-group">
      <label for="seed">Seed</label>
      <input 
        id="seed"
        v-model.number="chatControls.seed" 
        type="number" 
        class="form-input"
        placeholder="Leave empty for random"
      />
      <small class="form-hint">When supported, fixes sampling randomness for reproducibility</small>
    </div>

    <!-- Stop Sequences -->
    <div class="form-group">
      <label>Stop Sequences</label>
      <div class="stop-sequences-input">
        <input 
          v-model="newStopSequence"
          type="text" 
          class="form-input"
          placeholder="Add stop sequence..."
          @keydown.enter.prevent="addStopSequence"
        />
        <button type="button" @click="addStopSequence" class="action-btn">
          <i class="fa-solid fa-plus"></i>
        </button>
      </div>
      <div v-if="chatControls.stop.length" class="stop-sequences-list">
        <div v-for="(sequence, index) in chatControls.stop" :key="index" class="stop-sequence-item">
          <span>{{ sequence }}</span>
          <button type="button" @click="removeStopSequence(index)" class="remove-btn">
            <i class="fa-solid fa-times"></i>
          </button>
        </div>
      </div>
      <small class="form-hint">Strings that will stop generation when encountered</small>
    </div>

    <!-- JSON Mode -->
    <div class="form-group">
      <label for="json-mode">Structured / JSON Output</label>
      <select id="json-mode" v-model="chatControls.json_mode" class="form-select">
        <option value="off">Off</option>
        <option value="json_object">JSON Object</option>
        <option value="json_schema">JSON Schema</option>
      </select>
      <small class="form-hint">Guarantee valid JSON (and optionally a JSON Schema)</small>
    </div>

    <!-- Tool Choice -->
    <div class="form-group">
      <label for="tool-choice">Tool Choice</label>
      <select id="tool-choice" v-model="chatControls.tool_choice" class="form-select">
        <option value="auto">Auto</option>
        <option value="none">None</option>
        <option value="required">Required</option>
        <option value="by_name">By Name</option>
      </select>
      <small class="form-hint">How the model should choose tools</small>
    </div>

    <!-- Stream Responses -->
    <div class="form-group">
      <label class="form-checkbox-label">
        <input 
          v-model="chatControls.stream" 
          type="checkbox" 
          class="form-checkbox"
        />
        <span class="form-checkbox-custom"></span>
        Stream responses
      </label>
    </div>

    <!-- Ollama-specific controls -->
    <div class="form-advanced-section">
      <h4>Ollama-specific Controls</h4>
      
      <!-- Ollama Top-k -->
      <div class="form-group">
        <label for="ollama-top-k">Top-k</label>
        <div class="slider-group">
          <input 
            id="ollama-top-k"
            v-model.number="chatControls.ollama_top_k" 
            type="range" 
            min="1" 
            max="200" 
            step="1"
            class="form-slider"
          />
          <span class="slider-value">{{ chatControls.ollama_top_k }}</span>
        </div>
        <small class="form-hint">Limit vocabulary sampling to top-k tokens</small>
      </div>

      <!-- Ollama Repetition Penalty -->
      <div class="form-group">
        <label for="ollama-repeat-penalty">Repetition Penalty</label>
        <div class="slider-group">
          <input 
            id="ollama-repeat-penalty"
            v-model.number="chatControls.ollama_repeat_penalty" 
            type="range" 
            min="0.5" 
            max="2.0" 
            step="0.05"
            class="form-slider"
          />
          <span class="slider-value">{{ chatControls.ollama_repeat_penalty.toFixed(2) }}</span>
        </div>
        <small class="form-hint">Penalize repetitive text</small>
      </div>

      <!-- Ollama Mirostat -->
      <div class="form-group">
        <label for="ollama-mirostat">Mirostat Mode</label>
        <select id="ollama-mirostat" v-model.number="chatControls.ollama_mirostat" class="form-select">
          <option :value="0">0 (Disabled)</option>
          <option :value="1">1 (Mirostat 1.0)</option>
          <option :value="2">2 (Mirostat 2.0)</option>
        </select>
        <small class="form-hint">Advanced sampling algorithm</small>
      </div>

      <!-- Ollama Context Length -->
      <div class="form-group">
        <label for="ollama-num-ctx">Context Length (num_ctx)</label>
        <div class="slider-group">
          <input 
            id="ollama-num-ctx"
            v-model.number="chatControls.ollama_num_ctx" 
            type="range" 
            min="512" 
            max="32768" 
            step="512"
            class="form-slider"
          />
          <span class="slider-value">{{ chatControls.ollama_num_ctx }}</span>
        </div>
        <small class="form-hint">Maximum context length in tokens (default: 8192)</small>
      </div>
    </div>

    <!-- OpenAI Reasoning Model controls -->
    <div class="form-advanced-section">
      <h4>OpenAI Reasoning Model Controls</h4>
      
      <!-- Reasoning Effort -->
      <div class="form-group">
        <label for="reasoning-effort">Reasoning Effort</label>
        <select id="reasoning-effort" v-model="chatControls.reasoning_effort" class="form-select">
          <option value="minimal">Minimal</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        <small class="form-hint">Applies to reasoning models (o1*, o3*, gpt-5*)</small>
      </div>

      <!-- Verbosity -->
      <div class="form-group">
        <label for="verbosity">Verbosity</label>
        <select id="verbosity" v-model="chatControls.verbosity" class="form-select">
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        <small class="form-hint">Applies to gpt-5* models</small>
      </div>
    </div>

    <!-- Form Actions -->
    <div class="form-actions">
      <button type="button" @click="resetToDefaults" class="action-btn cancel-btn">
        <i class="fa-solid fa-undo"></i>
        Reset to Defaults
      </button>
      <button type="submit" class="action-btn save-btn">
        <i class="fa-solid fa-save"></i>
        Save Configuration
      </button>
    </div>
  </form>
  
  <!-- Notification Toast -->
  <div v-if="notification.isVisible.value" class="notification-toast" :class="notification.type.value">
    <i :class="notification.type.value === 'success' ? 'fa-solid fa-check' : 'fa-solid fa-exclamation-triangle'"></i>
    {{ notification.message.value }}
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/form.css';

/* Slider styling */
.slider-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.form-slider {
  flex: 1;
  height: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  outline: none;
  cursor: pointer;
  appearance: none;
  border-radius: 0;
}

.form-slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  background: linear-gradient(135deg, var(--border) 0%, var(--fg) 100%);
  border: 1px solid var(--fg);
  cursor: pointer;
  clip-path: polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%);
}

.form-slider::-webkit-slider-thumb:hover {
  background: linear-gradient(135deg, var(--fg) 0%, var(--accent) 100%);
  box-shadow: 0 0 6px var(--glow);
}

.slider-value {
  color: var(--fg);
  font-size: 0.9em;
  font-weight: 600;
  min-width: 60px;
  text-align: right;
  font-family: monospace;
}

/* Stop sequences */
.stop-sequences-input {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.stop-sequences-input .form-input {
  flex: 1;
}

.stop-sequences-input .action-btn {
  padding: 12px;
  min-width: auto;
}

.stop-sequences-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.stop-sequence-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 4px 8px;
  font-size: 0.85em;
  clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%);
}

.remove-btn {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  padding: 0;
  font-size: 0.8em;
}

.remove-btn:hover {
  color: var(--fg);
}

/* Advanced section headings */
.form-advanced-section h4 {
  color: var(--accent);
  font-size: 0.9em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 16px 0;
}

.notification-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 12px 16px;
  border-radius: 4px;
  color: white;
  font-weight: 600;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 250px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease;
}

.notification-toast.success {
  background: linear-gradient(135deg, #10b981, #059669);
  border: 1px solid #047857;
}

.notification-toast.error {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border: 1px solid #b91c1c;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>