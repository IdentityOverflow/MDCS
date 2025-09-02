<script setup lang="ts">
import { ref, nextTick } from 'vue'
import ChatControls from '../connections/ChatControls.vue'

// Props
interface Props {
  message: string
  showPanel: boolean
  panelType: 'controls' | 'menu'
  hasMessages: boolean
  isStreaming: boolean
  currentSessionId: string | null
  isSessionCancelling: boolean
  enableMarkdown: boolean
}

// Emits
interface Emits {
  (e: 'update:message', value: string): void
  (e: 'update:showPanel', value: boolean): void
  (e: 'update:panelType', value: 'controls' | 'menu'): void
  (e: 'sendMessage'): void
  (e: 'stopChat'): void
  (e: 'clearChat'): void
  (e: 'toggleMarkdown'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Local refs
const textareaRef = ref<HTMLTextAreaElement>()

// Handle keydown for Enter key
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    emit('sendMessage')
  }
}

// Auto-resize textarea
function autoResize() {
  const textarea = textareaRef.value
  if (textarea) {
    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto'
    // Set height to scrollHeight, but respect min/max constraints
    const newHeight = Math.min(Math.max(textarea.scrollHeight, 40), 120)
    textarea.style.height = `${newHeight}px`
  }
}

// Button handlers
function toggleControls() {
  if (props.showPanel && props.panelType === 'controls') {
    emit('update:showPanel', false)
  } else {
    emit('update:panelType', 'controls')
    emit('update:showPanel', true)
  }
}

function toggleMenu() {
  if (props.showPanel && props.panelType === 'menu') {
    emit('update:showPanel', false)
  } else {
    emit('update:panelType', 'menu')
    emit('update:showPanel', true)
  }
}

function handleSendMessage() {
  emit('sendMessage')
  // Reset textarea height after sending
  nextTick(() => {
    autoResize()
  })
}

function handleStopChat() {
  emit('stopChat')
}

function handleClearChat() {
  emit('clearChat')
}

function handleToggleMarkdown() {
  emit('toggleMarkdown')
}

// Handle input updates
function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:message', target.value)
  autoResize()
}
</script>

<template>
  <div class="floating-input-container">
    <div class="input-card">
      <!-- Panel (appears above input when active) -->
      <div v-if="showPanel" class="chat-controls-panel">
        <div class="controls-header">
          <h3>{{ panelType === 'controls' ? 'Chat Controls' : 'Chat Options' }}</h3>
          <button class="close-btn" @click="emit('update:showPanel', false)">
            <i class="fa-solid fa-times"></i>
          </button>
        </div>
        <div class="controls-content">
          <!-- Chat Controls Content -->
          <div v-if="panelType === 'controls'">
            <ChatControls />
          </div>
          <!-- Menu Options Content -->
          <div v-else-if="panelType === 'menu'" class="menu-options">
            <div class="option-item">
              <button class="option-toggle" @click="handleToggleMarkdown">
                <i :class="enableMarkdown ? 'fa-solid fa-check-square' : 'fa-regular fa-square'"></i>
                <span>Render Markdown</span>
              </button>
            </div>
            <div class="option-item">
              <button class="option-action clear-action" @click="handleClearChat(); emit('update:showPanel', false)">
                <i class="fa-solid fa-trash"></i>
                <span>Clear Chat</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Input row -->
      <div class="input-row">
        <div class="left-controls">
          <button 
            class="icon-btn settings-btn" 
            @click="toggleControls" 
            :class="{ active: showPanel && panelType === 'controls' }" 
            title="Chat Settings"
          >
            <i class="fa-solid fa-sliders"></i>
          </button>
          
          <button 
            v-if="hasMessages"
            class="icon-btn menu-btn" 
            @click="toggleMenu" 
            :class="{ active: showPanel && panelType === 'menu' }" 
            title="Chat Options"
          >
            <i class="fa-solid fa-ellipsis-vertical"></i>
          </button>
        </div>
        
        <div class="input-container">
          <textarea
            :value="message"
            @input="handleInput"
            @keydown="handleKeydown"
            placeholder="Use Shift+Enter for multi-line..."
            class="chat-input"
            ref="textareaRef"
            rows="1"
          ></textarea>
        </div>
        
        <div class="right-controls">
          <!-- Stop button when streaming/processing -->
          <button 
            v-if="isStreaming && currentSessionId"
            class="icon-btn stop-btn" 
            @click="handleStopChat" 
            :disabled="isSessionCancelling" 
            :title="isSessionCancelling ? 'Stopping...' : 'Stop Generation'"
          >
            <i :class="isSessionCancelling ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-stop'"></i>
          </button>
          
          <!-- Send button when not streaming -->
          <button 
            v-else
            class="icon-btn send-btn" 
            @click="handleSendMessage" 
            :disabled="!message.trim()" 
            title="Send Message"
          >
            <i class="fa-solid fa-paper-plane"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Floating input container */
.floating-input-container {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 48px);
  max-width: 600px;
  z-index: 10;
}

.input-card {
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border: 1px solid var(--border);
  border-radius: 0;
  box-shadow: 
    0 0 20px rgba(0, 212, 255, 0.2),
    inset 0 0 10px rgba(0, 212, 255, 0.1);
  clip-path: polygon(0 0, 108% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%);
  position: relative;
}

.input-card::before {
  content: '';
  position: absolute;
  bottom: 6px;
  right: 0;
  width: 12px;
  height: 1px;
  background: var(--border);
  transform: rotate(-45deg);
  transform-origin: right center;
}

/* Chat Controls panel */
.chat-controls-panel {
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  max-height: 60vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.controls-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
}

.controls-header h3 {
  color: var(--fg);
  font-size: 1em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: var(--fg);
  cursor: pointer;
  font-size: 1.2em;
  opacity: 0.7;
  transition: opacity 0.2s ease;
  padding: 4px;
}

.close-btn:hover {
  opacity: 1;
  color: var(--accent);
}

.controls-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* Input row */
.input-row {
  display: flex;
  align-items: flex-end;
  padding: 12px;
  gap: 8px;
}

.left-controls,
.right-controls {
  display: flex;
  gap: 6px;
}

.input-container {
  flex: 1;
}

.chat-input {
  width: 100%;
  background: transparent;
  border: none;
  color: var(--fg);
  padding: 8px 12px;
  font-size: 0.95em;
  font-weight: 400;
  font-family: inherit;
  resize: none;
  height: 40px;
  min-height: 40px;
  max-height: 120px;
  line-height: 1.4;
  overflow-y: hidden;
  transition: height 0.1s ease;
}

.chat-input:focus {
  outline: none;
}

.chat-input::placeholder {
  color: var(--fg);
  opacity: 0.4;
}

/* Icon buttons */
.icon-btn {
  position: relative;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--fg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 0.85em;
  opacity: 0.7;
  clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%);
}

.icon-btn:hover:not(:disabled) {
  opacity: 1;
  background: rgba(0, 212, 255, 0.1);
  border-color: var(--fg);
}

.icon-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.icon-btn.active {
  background: rgba(0, 212, 255, 0.2);
  border-color: var(--fg);
  opacity: 1;
}

.send-btn:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
}

.send-btn:not(:disabled) {
  opacity: 1;
}

.stop-btn:hover:not(:disabled) {
  color: #ef4444;
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.stop-btn:not(:disabled) {
  opacity: 1;
  color: #f59e0b;
  border-color: #f59e0b;
}

/* Menu options styling */
.menu-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-item {
  display: flex;
}

.option-toggle,
.option-action {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: none;
  border: 1px solid var(--border);
  color: var(--fg);
  font-size: 0.9em;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 4px;
}

.option-toggle:hover,
.option-action:hover {
  background: rgba(120, 120, 120, 0.1);
  border-color: var(--fg);
}

.option-toggle i,
.option-action i {
  width: 16px;
  text-align: center;
  font-size: 0.9em;
}

.option-action.clear-action:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: #ef4444;
}
</style>