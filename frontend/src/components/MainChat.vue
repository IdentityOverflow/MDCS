<script setup lang="ts">
import { ref, nextTick, computed, onMounted } from 'vue'
import ChatControls from './connections/ChatControls.vue'
import { useChat, type ChatMessage } from '@/composables/useChat'
import { useLocalStorage } from '@/composables/storage'
import { usePersonas } from '@/composables/usePersonas'

const message = ref('')
const showSliders = ref(false)
const textareaRef = ref<HTMLTextAreaElement>()

// Chat functionality
const { 
  messages, 
  isStreaming, 
  currentStreamingMessage, 
  error, 
  hasMessages, 
  sendChatMessage, 
  clearChat 
} = useChat()

// Get chat controls from storage - no defaults, load what's actually saved
const { data: chatControls, load: loadChatControls } = useLocalStorage({
  key: 'chat-controls',
  defaultValue: {
    provider: 'ollama',
    selectedPersonaId: '',
    stream: true,
    // All other settings come from ChatControls component
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
    ollama_top_k: 40,
    ollama_repeat_penalty: 1.1,
    ollama_mirostat: 0,
    ollama_num_ctx: 8192,
    reasoning_effort: 'low',
    verbosity: 'medium'
  }
})

// Load chat controls on component mount
onMounted(() => {
  loadChatControls()
})

// Personas for system prompt
const { getPersonaById } = usePersonas()

// Computed values
const selectedPersona = computed(() => {
  return chatControls.value.selectedPersonaId ? 
    getPersonaById(chatControls.value.selectedPersonaId) : null
})

const currentSystemPrompt = computed(() => {
  return selectedPersona.value?.template || ''
})

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

async function sendMessage() {
  if (!message.value.trim() || isStreaming.value) return
  
  const userMessage = message.value.trim()
  message.value = ''
  
  // Reset textarea height after sending
  nextTick(() => {
    autoResize()
  })
  
  try {
    await sendChatMessage(
      userMessage,
      chatControls.value as any,
      currentSystemPrompt.value
    )
  } catch (error) {
    console.error('Failed to send message:', error)
  }
}

function toggleSliders() {
  showSliders.value = !showSliders.value
}

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

// Format timestamp for display
function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

// Clear chat history
function handleClearChat() {
  clearChat()
}
</script>

<template>
  <div class="main-chat">
    <!-- Chat messages area -->
    <div class="chat-content">
      <div class="chat-messages" :class="{ 'has-messages': hasMessages }">
        <!-- Chat messages -->
        <div v-if="hasMessages" class="messages-list">
          <div 
            v-for="msg in messages" 
            :key="msg.id" 
            class="message" 
            :class="[`message-${msg.role}`, { 'system-message': msg.role === 'system' }]"
            v-show="msg.role !== 'system'"
          >
            <div class="message-content">
              <div class="message-text">{{ msg.content }}</div>
              <div class="message-meta">
                <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
                <span v-if="msg.metadata?.model" class="message-model">{{ msg.metadata.model }}</span>
                <span v-if="msg.metadata?.tokens_used" class="message-tokens">{{ msg.metadata.tokens_used }} tokens</span>
              </div>
            </div>
          </div>
          
          <!-- Streaming message -->
          <div v-if="isStreaming && currentStreamingMessage" class="message message-assistant streaming">
            <div class="message-content">
              <div class="message-text">{{ currentStreamingMessage }}<span class="streaming-cursor">▋</span></div>
              <div class="message-meta">
                <span class="streaming-indicator">
                  <i class="fa-solid fa-circle-notch fa-spin"></i>
                  Typing...
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Empty state -->
        <div v-else class="empty-state">
          <div class="placeholder-text">Start a conversation...</div>
          <div class="placeholder-hint">
            <div v-if="selectedPersona" class="active-persona">
              <i class="fa-solid fa-user-robot"></i>
              Active Persona: {{ selectedPersona.name }}
            </div>
            <div class="provider-info">
              <i class="fa-solid fa-server"></i>
              Provider: {{ chatControls.provider.toUpperCase() }}
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Floating input container -->
    <div class="floating-input-container">
      <div class="input-card">
        <!-- Chat Controls panel (appears above input when active) -->
        <div v-if="showSliders" class="chat-controls-panel">
          <div class="controls-header">
            <h3>Chat Controls</h3>
            <button class="close-btn" @click="toggleSliders">
              <i class="fa-solid fa-times"></i>
            </button>
          </div>
          <div class="controls-content">
            <ChatControls />
          </div>
        </div>
        
        <!-- Input row -->
        <div class="input-row">
          <div class="left-controls">
            <button 
              class="icon-btn settings-btn" 
              @click="toggleSliders" 
              :class="{ active: showSliders }" 
              title="Chat Settings"
            >
              <i class="fa-solid fa-sliders"></i>
            </button>
            <button 
              v-if="hasMessages"
              class="icon-btn clear-btn" 
              @click="handleClearChat" 
              title="Clear Chat"
            >
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
          
          <div class="input-container">
            <textarea
              v-model="message"
              @keydown="handleKeydown"
              @input="autoResize"
              placeholder="Use Shift+Enter for multi-line..."
              class="chat-input"
              ref="textareaRef"
              rows="1"
            ></textarea>
          </div>
          
          <div class="right-controls">
            <button 
              class="icon-btn send-btn" 
              @click="sendMessage" 
              :disabled="!message.trim() || isStreaming" 
              :title="isStreaming ? 'Sending...' : 'Send Message'"
            >
              <i :class="isStreaming ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-paper-plane'"></i>
            </button>
          </div>
        </div>
      </div>
      
    </div>
  </div>
</template>

<style scoped>
.main-chat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  grid-area: A;
  position: relative;
  overflow: hidden;
}

.chat-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  padding: 32px 16px 120px;
  overflow-y: auto;
}

.chat-messages:not(.has-messages) {
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-text {
  color: var(--fg);
  opacity: 0.4;
  font-size: 1.1em;
  font-weight: 300;
}

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

/* Chat Messages Styling */
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 80%;
  animation: messageSlideIn 0.3s ease-out;
}

.message-user {
  align-self: flex-end;
}

.message-assistant {
  align-self: flex-start;
}

.message-content {
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 12px 16px;
  position: relative;
}

.message-user .message-content {
  background: linear-gradient(135deg, var(--accent) 0%, rgba(0, 212, 255, 0.8) 100%);
  color: var(--bg);
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%);
}

.message-assistant .message-content {
  background: var(--surface);
  color: var(--fg);
  clip-path: polygon(8px 0, 100% 0, 100% 100%, 0 100%, 0 8px);
}

.message-text {
  font-size: 0.95em;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  font-size: 0.8em;
  opacity: 0.7;
}

.message-time,
.message-model,
.message-tokens {
  font-family: monospace;
}

.message-user .message-meta {
  color: rgba(255, 255, 255, 0.8);
}

.message-assistant .message-meta {
  color: var(--fg-secondary);
}

/* Streaming message */
.message.streaming .message-content {
  border-color: var(--accent);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

.streaming-cursor {
  animation: blink 1s infinite;
  color: var(--accent);
}

.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--accent);
}

/* Empty state styling */
.empty-state {
  text-align: center;
}

.placeholder-hint {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.85em;
  opacity: 0.6;
}

.active-persona,
.provider-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.active-persona {
  color: var(--accent);
}

/* Clear button styling */
.clear-btn:hover:not(:disabled) {
  color: #ef4444;
  border-color: #ef4444;
}

/* Animations */
@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

</style>