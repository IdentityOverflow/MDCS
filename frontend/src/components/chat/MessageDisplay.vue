<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ChatMessage } from '@/composables/useChat'
import { useMarkdown } from '@/composables/useMarkdown'
import { useThinkingToggle } from '@/composables/useThinkingToggle'

// Props
interface Props {
  messages: ChatMessage[]
  hasMessages: boolean
  isStreaming: boolean
  currentStreamingMessage: string
  currentStreamingThinking: string
  processingStage: string | null
  stageMessage: string | null
  isProcessingAfter: boolean
  enableMarkdown: boolean
  selectedPersona?: { name: string } | null
  provider: string
  // Message editing props
  editingMessageId: string | null
  editingContent: string
  editingThinking: string
}

// Emits
interface Emits {
  (e: 'toggleThinking', messageId: string): void
  (e: 'startEditMessage', messageId: string): void
  (e: 'cancelEditMessage'): void
  (e: 'saveEditMessage'): void
  (e: 'deleteMessage', messageId: string): void
  (e: 'update:editingContent', value: string): void
  (e: 'update:editingThinking', value: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Composables
const { parseMarkdown } = useMarkdown()
const { expandedThinking, toggleThinking, expandThinking } = useThinkingToggle()

// Computed values
const streamingMessageWithCursor = computed(() => {
  if (!props.currentStreamingMessage) return ''
  const content = props.enableMarkdown 
    ? parseMarkdown(props.currentStreamingMessage) 
    : props.currentStreamingMessage.replace(/\n/g, '<br>')
  return content + '<span class="streaming-cursor">▋</span>'
})

// Helper function to render message content
const renderMessageContent = (content: string): string => {
  if (props.enableMarkdown) {
    return parseMarkdown(content)
  } else {
    return content.replace(/\n/g, '<br>')
  }
}

// Format timestamp for display
function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

// Check if message can be edited
function canEditMessage(msg: ChatMessage): boolean {
  return msg.role !== 'system'
}

// Get streaming indicator text
function getStreamingIndicatorText(): string {
  if (props.processingStage) {
    switch (props.processingStage) {
      case 'thinking':
        return props.isProcessingAfter ? 'Processing...' : 'Thinking...'
      case 'generating':
        return 'Typing...'
      default:
        return props.stageMessage || 'Processing...'
    }
  }
  return 'Typing...'
}

// Message editing functions
function handleToggleThinking(messageId: string) {
  toggleThinking(messageId)
  emit('toggleThinking', messageId)
}

function handleStartEditMessage(messageId: string) {
  emit('startEditMessage', messageId)
  // Expand thinking if it exists to show in edit mode
  const msg = props.messages.find(m => m.id === messageId)
  if (msg?.thinking) {
    expandThinking(messageId)
  }
}

function handleSaveEditMessage() {
  emit('saveEditMessage')
}

function handleCancelEditMessage() {
  emit('cancelEditMessage')
}

function handleDeleteMessage(messageId: string) {
  emit('deleteMessage', messageId)
}
</script>

<template>
  <div ref="chatMessagesRef" class="chat-messages" :class="{ 'has-messages': hasMessages }">
    <!-- Messages List -->
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
              <button class="card-icon-btn save-btn" @click="handleSaveEditMessage" title="Save changes">
                <i class="fa-solid fa-check"></i>
              </button>
              <button class="card-icon-btn cancel-btn" @click="handleCancelEditMessage" title="Cancel editing">
                <i class="fa-solid fa-times"></i>
              </button>
            </template>
            <template v-else>
              <!-- Edit/Delete buttons when not editing -->
              <button class="card-icon-btn edit-btn" @click="handleStartEditMessage(msg.id)" title="Edit message">
                <i class="fa-solid fa-edit"></i>
              </button>
              <button class="card-icon-btn delete-btn" @click="handleDeleteMessage(msg.id)" title="Delete message">
                <i class="fa-solid fa-trash"></i>
              </button>
            </template>
          </div>

          <!-- Thinking content (if available) -->
          <div v-if="msg.thinking || (editingMessageId === msg.id)" class="message-thinking">
            <button 
              @click="handleToggleThinking(msg.id)"
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
                :value="editingThinking"
                @input="emit('update:editingThinking', ($event.target as HTMLTextAreaElement).value)"
                class="thinking-edit-textarea"
                placeholder="Add thinking process (optional)..."
                rows="3"
              ></textarea>
              <!-- Display thinking content -->
              <div v-else class="thinking-text">{{ msg.thinking }}</div>
            </div>
          </div>
          
          <!-- Message content -->
          <!-- Editable message content -->
          <textarea
            v-if="editingMessageId === msg.id"
            :value="editingContent"
            @input="emit('update:editingContent', ($event.target as HTMLTextAreaElement).value)"
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
      
      <!-- BEFORE processing indicator -->
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

      <!-- Active streaming indicator -->
      <div v-if="isStreaming && (currentStreamingMessage || currentStreamingThinking)" class="message message-assistant streaming">
        <div class="message-content">
          <!-- Streaming thinking content -->
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
          Provider: {{ provider.toUpperCase() }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/card.css';

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

/* Messages list */
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

/* Message meta */
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

/* Streaming indicators */
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

.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--accent);
  opacity: 0.8;
  font-size: 0.85em;
}

/* Streaming message */
.message.streaming .message-content {
  border-color: var(--accent);
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

/* Processing placeholder */
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

/* Thinking content */
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

/* Empty state */
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

/* Message actions */
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

/* Button styles */
.card-icon-btn.save-btn:hover {
  color: #22c55e;
  border-color: #22c55e;
}

.card-icon-btn.cancel-btn:hover {
  color: #f59e0b;
  border-color: #f59e0b;
}

/* Message editing */
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