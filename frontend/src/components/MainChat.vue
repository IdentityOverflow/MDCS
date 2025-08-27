<script setup lang="ts">
import { ref, nextTick, computed, onMounted, onUnmounted, watch } from 'vue'
import ChatControls from './connections/ChatControls.vue'
import { useChat, type ChatMessage, type ChatControls as ChatControlsType } from '@/composables/useChat'
import { useLocalStorage } from '@/composables/storage'
import { usePersonas } from '@/composables/usePersonas'
import { useMarkdown } from '@/composables/useMarkdown'

const message = ref('')
const showPanel = ref(false)
const panelType = ref<'controls' | 'menu'>('controls')
const textareaRef = ref<HTMLTextAreaElement>()
const chatMessagesRef = ref<HTMLElement>()

// Menu options
const enableMarkdown = ref(true)

// Thinking content visibility tracking
const expandedThinking = ref<Set<string>>(new Set())

// Message editing state
const editingMessageId = ref<string | null>(null)
const editingContent = ref<string>('')
const editingThinking = ref<string>('')

// Chat functionality
const { 
  messages, 
  isStreaming, 
  currentStreamingMessage,
  currentStreamingThinking, 
  hasMessages, 
  sendChatMessage, 
  clearChat,
  removeMessage,
  updateMessage,
  processingStage,
  stageMessage,
  isProcessingAfter,
  messageCompleted,
  hideStreamingUI
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
    thinking_enabled: false,
    ollama_top_k: 40,
    ollama_repeat_penalty: 1.1,
    ollama_mirostat: 0,
    ollama_num_ctx: 8192,
    reasoning_effort: 'low',
    verbosity: 'medium'
  }
})

// Click outside handler to close panel
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.chat-controls-panel') && !target.closest('.left-controls')) {
    showPanel.value = false
  }
}

// Load chat controls on component mount
onMounted(() => {
  loadChatControls()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

// Auto-scroll watchers
watch(messages, () => {
  scrollToBottom()
}, { deep: true })

watch([currentStreamingMessage, currentStreamingThinking], () => {
  if (isStreaming.value) {
    scrollToBottom()
  }
})

// Personas for system prompt
const { getPersonaById } = usePersonas()

// Markdown parsing
const { parseMarkdown } = useMarkdown()

// Computed values
const selectedPersona = computed(() => {
  return chatControls.value.selectedPersonaId ? 
    getPersonaById(chatControls.value.selectedPersonaId) : null
})

const currentSystemPrompt = computed(() => {
  return selectedPersona.value?.template || ''
})

const streamingMessageWithCursor = computed(() => {
  if (!currentStreamingMessage.value) return ''
  const content = enableMarkdown.value 
    ? parseMarkdown(currentStreamingMessage.value) 
    : currentStreamingMessage.value.replace(/\n/g, '<br>')
  return content + '<span class="streaming-cursor">▋</span>'
})

// Helper function to render message content based on markdown setting
const renderMessageContent = (content: string): string => {
  if (enableMarkdown.value) {
    return parseMarkdown(content)
  } else {
    return content.replace(/\n/g, '<br>')
  }
}

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
      chatControls.value as ChatControlsType,
      currentSystemPrompt.value
    )
    // Scroll to bottom after sending message
    scrollToBottom()
  } catch (error) {
    console.error('Failed to send message:', error)
  }
}

function toggleControls() {
  if (showPanel.value && panelType.value === 'controls') {
    showPanel.value = false
  } else {
    panelType.value = 'controls'
    showPanel.value = true
  }
}

function toggleMenu() {
  if (showPanel.value && panelType.value === 'menu') {
    showPanel.value = false
  }
 else {
    panelType.value = 'menu'
    showPanel.value = true
  }
}

function toggleMarkdown() {
  enableMarkdown.value = !enableMarkdown.value
}

// Scroll to bottom function
function scrollToBottom() {
  nextTick(() => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    }
  })
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
  if (confirm('Are you sure you want to clear this conversation? This will permanently delete all messages and cannot be undone.')) {
    clearChat()
  }
}

// Toggle thinking content visibility
function toggleThinking(messageId: string) {
  const expanded = expandedThinking.value
  if (expanded.has(messageId)) {
    expanded.delete(messageId)
  } else {
    expanded.add(messageId)
  }
}

// Message editing functions
function startEditMessage(messageId: string) {
  const msg = messages.value.find(m => m.id === messageId)
  if (msg) {
    editingMessageId.value = messageId
    editingContent.value = msg.content
    editingThinking.value = msg.thinking || ''
    // Expand thinking if it exists to show in edit mode
    if (msg.thinking) {
      expandedThinking.value.add(messageId)
    }
  }
}

function cancelEditMessage() {
  editingMessageId.value = null
  editingContent.value = ''
  editingThinking.value = ''
}

async function saveEditMessage() {
  if (!editingMessageId.value) return
  
  try {
    await updateMessage(editingMessageId.value, {
      content: editingContent.value.trim(),
      thinking: editingThinking.value.trim() || undefined
    })
    cancelEditMessage()
  } catch (error) {
    console.error('Failed to update message:', error)
    alert('Failed to update message. Please try again.')
  }
}

async function deleteMessage(messageId: string) {
  if (!confirm('Are you sure you want to delete this message?')) {
    return
  }
  
  try {
    await removeMessage(messageId)
  } catch (error) {
    console.error('Failed to delete message:', error)
    alert('Failed to delete message. Please try again.')
  }
}

// Check if message can be edited (not system messages and not currently streaming)
function canEditMessage(msg: ChatMessage): boolean {
  return msg.role !== 'system' && !isStreaming.value
}

// Get streaming indicator text based on processing stage
function getStreamingIndicatorText(): string {
  console.log('DEBUG Template: messageCompleted:', messageCompleted.value, 'isStreaming:', isStreaming.value, 'currentStreamingMessage:', !!currentStreamingMessage.value, 'currentStreamingThinking:', !!currentStreamingThinking.value)
  
  if (processingStage.value) {
    switch (processingStage.value) {
      case 'thinking':
        return isProcessingAfter.value ? 'Processing...' : 'Thinking...'
      case 'generating':
        return 'Typing...'
      default:
        return stageMessage.value || 'Processing...'
    }
  }
  return 'Typing...'
}
</script>

<template>
  <div class="main-chat">
    <!-- Chat messages area -->
    <div class="chat-content">
      <div ref="chatMessagesRef" class="chat-messages" :class="{ 'has-messages': hasMessages }">
        <!-- Chat messages -->
        <div v-if="hasMessages" class="messages-list">
          <div 
            v-for="msg in messages" 
            :key="msg.id" 
            class="message" 
            :class="[`message-${msg.role}`, { 'system-message': msg.role === 'system', 'editing': editingMessageId === msg.id }]"
            v-show="msg.role !== 'system'"
          >
            <div class="message-content">
              <!-- Message actions (edit/delete buttons) -->
              <div v-if="canEditMessage(msg)" class="message-actions">
                <template v-if="editingMessageId === msg.id">
                  <!-- Save/Cancel buttons when editing -->
                  <button class="card-icon-btn save-btn" @click="saveEditMessage" title="Save changes">
                    <i class="fa-solid fa-check"></i>
                  </button>
                  <button class="card-icon-btn cancel-btn" @click="cancelEditMessage" title="Cancel editing">
                    <i class="fa-solid fa-times"></i>
                  </button>
                </template>
                <template v-else>
                  <!-- Edit/Delete buttons when not editing -->
                  <button class="card-icon-btn edit-btn" @click="startEditMessage(msg.id)" title="Edit message">
                    <i class="fa-solid fa-edit"></i>
                  </button>
                  <button class="card-icon-btn delete-btn" @click="deleteMessage(msg.id)" title="Delete message">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </template>
              </div>

              <!-- Thinking content (if available) - shown above response -->
              <div v-if="msg.thinking || (editingMessageId === msg.id)" class="message-thinking">
                <button 
                  @click="toggleThinking(msg.id)"
                  class="thinking-toggle"
                  :class="{ 'expanded': expandedThinking.has(msg.id) }"
                >
                  <i class="fa-solid fa-brain"></i>
                  <span>{{ editingMessageId === msg.id ? 'Edit Thinking Process' : 'Thinking Process' }}</span>
                  <i class="fa-solid fa-chevron-down toggle-icon"></i>
                </button>
                <div 
                  v-show="expandedThinking.has(msg.id)" 
                  class="thinking-content"
                >
                  <!-- Editable thinking content -->
                  <textarea
                    v-if="editingMessageId === msg.id"
                    v-model="editingThinking"
                    class="thinking-edit-textarea"
                    placeholder="Add thinking process (optional)..."
                    rows="3"
                  ></textarea>
                  <!-- Display thinking content -->
                  <div v-else class="thinking-text">{{ msg.thinking }}</div>
                </div>
              </div>
              
              <!-- Regular message content -->
              <!-- Editable message content -->
              <textarea
                v-if="editingMessageId === msg.id"
                v-model="editingContent"
                class="message-edit-textarea"
                placeholder="Edit message..."
                rows="3"
              ></textarea>
              <!-- Display message content -->
              <div v-else class="message-text" :class="{ 'plain-text': !enableMarkdown }" v-html="renderMessageContent(msg.content)"></div>
              
              <div class="message-meta">
                <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
                <span v-if="msg.metadata?.model" class="message-model">{{ msg.metadata.model }}</span>
                <span v-if="msg.metadata?.tokens_used" class="message-tokens">{{ msg.metadata.tokens_used }} tokens</span>
                <span v-if="msg.thinking" class="thinking-indicator">
                  <i class="fa-solid fa-brain"></i>
                  Has reasoning
                </span>
              </div>
            </div>
          </div>
          
          <!-- BEFORE processing indicator - minimal spinner only (for both streaming and non-streaming) -->
          <div v-if="processingStage === 'thinking' && !currentStreamingMessage && !currentStreamingThinking && !isProcessingAfter" class="message message-assistant streaming">
            <div class="message-content">
              <div class="message-meta">
                <span class="streaming-indicator">
                  <i class="fa-solid fa-circle-notch fa-spin"></i>
                  Thinking...
                </span>
              </div>
            </div>
          </div>


          <!-- Active streaming indicator (only show when UI not hidden) -->
          <div v-if="!hideStreamingUI && isStreaming && (currentStreamingMessage || currentStreamingThinking)" class="message message-assistant streaming">
            <div class="message-content">
              <!-- Streaming thinking content - shown above response (only during initial thinking) -->
              <div v-if="currentStreamingThinking" class="message-thinking streaming-thinking">
                <div class="thinking-toggle expanded">
                  <i class="fa-solid fa-brain"></i>
                  <span>Thinking Process (Live)</span>
                  <i class="fa-solid fa-circle-notch fa-spin"></i>
                </div>
                <div class="thinking-content" style="display: block;">
                  <div class="thinking-text streaming">{{ currentStreamingThinking }}<span class="streaming-cursor">▋</span></div>
                </div>
              </div>
              
              <!-- Show streaming message content if available -->
              <div v-if="currentStreamingMessage" class="message-text" v-html="streamingMessageWithCursor"></div>
              
              <!-- Show processing indicator for generating stage -->
              <div v-else-if="processingStage === 'generating' && !currentStreamingMessage" class="processing-placeholder">
                <i class="fa-solid fa-comment-dots"></i>
                <span>{{ stageMessage || 'Generating response...' }}</span>
              </div>
              
              <div class="message-meta">
                <span class="streaming-indicator">
                  <i class="fa-solid fa-circle-notch fa-spin"></i>
                  {{ getStreamingIndicatorText() }}
                </span>
                <span v-if="currentStreamingThinking" class="thinking-indicator">
                  <i class="fa-solid fa-brain"></i>
                  Reasoning...
                </span>
              </div>
            </div>
          </div>

          <!-- No visual feedback during AFTER processing - let it run silently in background -->

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
        <!-- Panel (appears above input when active) -->
        <div v-if="showPanel" class="chat-controls-panel">
          <div class="controls-header">
            <h3>{{ panelType === 'controls' ? 'Chat Controls' : 'Chat Options' }}</h3>
            <button class="close-btn" @click="showPanel = false">
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
                <button class="option-toggle" @click="toggleMarkdown">
                  <i :class="enableMarkdown ? 'fa-solid fa-check-square' : 'fa-regular fa-square'"></i>
                  <span>Render Markdown</span>
                </button>
              </div>
              <div class="option-item">
                <button class="option-action clear-action" @click="handleClearChat(); showPanel = false">
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
@import '@/assets/card.css';

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
  word-wrap: break-word;
}

.message-text.plain-text {
  white-space: pre-wrap;
}

/* Markdown content styling - using :deep() to penetrate scoped styles */
:deep(.message-text h1),
:deep(.message-text h2),
:deep(.message-text h3),
:deep(.message-text h4),
:deep(.message-text h5),
:deep(.message-text h6) {
  margin: 0.4em 0 0.2em 0;
  color: inherit;
  font-weight: 600;
  line-height: 1.2;
}

:deep(.message-text h1) { font-size: 1.3em; }
:deep(.message-text h2) { font-size: 1.2em; }
:deep(.message-text h3) { font-size: 1.1em; }
:deep(.message-text h4) { font-size: 1.05em; }
:deep(.message-text h5) { font-size: 1.02em; }
:deep(.message-text h6) { font-size: 1em; }

:deep(.message-text p) {
  margin: 0;
  line-height: 1.5;
}

:deep(.message-text p + p) {
  margin-top: 0.4em;
}

:deep(.message-text strong) {
  font-weight: 700;
  color: inherit;
}

:deep(.message-text em) {
  font-style: italic;
  color: inherit;
}

:deep(.message-text code) {
  background: rgba(120, 120, 120, 0.15);
  padding: 2px 4px;
  border-radius: 2px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  color: var(--accent);
}

:deep(.message-text pre) {
  background: rgba(120, 120, 120, 0.1);
  border: 1px solid rgba(120, 120, 120, 0.2);
  border-radius: 4px;
  padding: 12px;
  margin: 0.3em 0;
  overflow-x: auto;
}

:deep(.message-text pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

:deep(.message-text blockquote) {
  border-left: 3px solid var(--accent);
  margin: 0.3em 0;
  padding: 0 12px;
  color: inherit;
  opacity: 0.9;
  font-style: italic;
}

:deep(.message-text ul),
:deep(.message-text ol) {
  margin: 0.2em 0;
  padding-left: 20px;
}

:deep(.message-text li) {
  margin: 0;
  line-height: 1.4;
}

:deep(.message-text a) {
  color: var(--accent);
  text-decoration: underline;
}

:deep(.message-text a:hover) {
  color: var(--fg);
}

/* Ensure line breaks are properly rendered */
:deep(.message-text br) {
  line-height: 1.5;
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

/* Processing placeholder styles */
.processing-placeholder {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  color: var(--fg-secondary);
  font-style: italic;
  opacity: 0.8;
}

.processing-placeholder i {
  font-size: 1.1em;
  color: var(--accent);
  opacity: 0.7;
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

.after-thinking-indicator {
  display: flex;
  justify-content: center;
  padding: 8px;
  opacity: 0.5;
}

.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--accent);
  opacity: 0.8;
  font-size: 0.85em;
}

/* Thinking content styles */
.message-thinking {
  margin: 12px 0;
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 4px;
  overflow: hidden;
  background: rgba(0, 212, 255, 0.05);
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  background: rgba(120, 120, 120, 0.08);
  border: none;
  padding: 8px 12px;
  color: var(--fg-secondary);
  cursor: pointer;
  font-size: 0.9em;
  transition: all 0.2s ease;
}

.thinking-toggle:hover {
  background: rgba(120, 120, 120, 0.12);
  color: var(--fg-primary);
}

.thinking-toggle .toggle-icon {
  margin-left: auto;
  transition: transform 0.2s ease;
}

.thinking-toggle.expanded .toggle-icon {
  transform: rotate(180deg);
}

.thinking-content {
  padding: 12px;
  border-top: 1px solid rgba(120, 120, 120, 0.15);
  animation: fadeIn 0.2s ease;
}

.thinking-text {
  font-size: 0.9em;
  line-height: 1.5;
  color: var(--fg-tertiary);
  font-style: italic;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.thinking-text.streaming {
  color: var(--fg-secondary);
}

.streaming-thinking .thinking-toggle {
  background: rgba(120, 120, 120, 0.12);
  color: var(--fg-primary);
}

.streaming-thinking .thinking-content {
  background: rgba(120, 120, 120, 0.03);
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

/* Message actions (edit/delete buttons) */
.message-actions {
  position: absolute;
  bottom: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
  z-index: 10;
}

.message:hover .message-actions {
  opacity: 1;
}

.message.editing .message-actions {
  opacity: 1;
}

/* Additional button styles for save/cancel */
.card-icon-btn.save-btn:hover {
  color: #22c55e;
  border-color: #22c55e;
}

.card-icon-btn.cancel-btn:hover {
  color: #f59e0b;
  border-color: #f59e0b;
}

/* Message editing styles */
.message.editing {
  max-width: 80%;
  min-width: 600px;
}

.message.editing .message-content {
  border-color: var(--accent);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.2);
}

.message-edit-textarea,
.thinking-edit-textarea {
  width: 100%;
  box-sizing: border-box;
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--fg);
  padding: 8px 12px;
  font-size: 0.95em;
  font-family: inherit;
  line-height: 1.5;
  resize: vertical;
  min-height: 80px;
  border-radius: 4px;
  transition: border-color 0.2s ease;
}

.message-edit-textarea:focus,
.thinking-edit-textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 5px rgba(0, 212, 255, 0.3);
}

.thinking-edit-textarea {
  min-height: 60px;
  font-style: italic;
  background: rgba(0, 212, 255, 0.02);
}

.message-edit-textarea::placeholder,
.thinking-edit-textarea::placeholder {
  color: var(--fg-secondary);
  opacity: 0.6;
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

@keyframes fadeIn {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 200px;
  }
}

</style>