<script setup lang="ts">
import { ref, nextTick, computed, onMounted, onUnmounted, watch } from 'vue'
import ChatInput from './ChatInput.vue'
import { useChat, type ChatControls as ChatControlsType } from '@/composables/useChat'
import { useLocalStorage } from '@/composables/storage'
import { usePersonas } from '@/composables/usePersonas'
import { useMarkdown } from '@/composables/useMarkdown'
import { useMessageActions } from '@/composables/useMessageActions'
import { useScrollToBottom } from '@/composables/useScrollToBottom'
import { useThinkingToggle } from '@/composables/useThinkingToggle'
import MessageDisplay from './MessageDisplay.vue'

const chatMessagesRef = ref<HTMLElement>()

// Chat input state
const message = ref('')
const showPanel = ref(false)
const panelType = ref<'controls' | 'menu'>('controls')

// Menu options
const enableMarkdown = ref(true)

// Thinking content visibility
const { expandedThinking, toggleThinking, expandThinking } = useThinkingToggle()

// Message editing functionality
const {
  editingMessageId,
  editingContent,
  editingThinking,
  startEditMessage,
  cancelEditMessage,
  saveEditMessage,
  deleteMessage
} = useMessageActions()

// Chat functionality
const {
  messages,
  isStreaming,
  currentStreamingMessage,
  currentStreamingThinking,
  hasMessages,
  sendChatMessage,
  clearChat,
  clearMemories,
  processingStage,
  stageMessage,
  isProcessingAfter,
  // Session management
  currentSessionId,
  cancelCurrentSession,
  isSessionCancelling,
  // WebSocket management
  isWebSocketConnected,
  isWebSocketConnecting,
  connectWebSocket,
  disconnectWebSocket
} = useChat()

// Scroll functionality - initialized after chat composables
const { scrollToBottom, setupAutoScroll } = useScrollToBottom(
  messages, 
  isStreaming, 
  currentStreamingMessage, 
  currentStreamingThinking
)

// Get chat controls from storage - no defaults, load what's actually saved
const { data: chatControls, load: loadChatControls } = useLocalStorage({
  key: 'chat-controls',
  defaultValue: {
    provider: 'ollama',
    selected_model: '',
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
onMounted(async () => {
  loadChatControls()
  document.addEventListener('click', handleClickOutside)
  setupAutoScroll(chatMessagesRef)

  // Connect to WebSocket
  try {
    console.log('🔌 Connecting to WebSocket...')
    await connectWebSocket()
    console.log('✅ WebSocket connected')
  } catch (err) {
    console.error('Failed to connect WebSocket:', err)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)

  // Disconnect WebSocket on unmount
  try {
    disconnectWebSocket()
  } catch (err) {
    console.error('Failed to disconnect WebSocket:', err)
  }
})

// Auto-scroll is now handled by useScrollToBottom composable

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



// Chat input handlers
async function handleSendMessage() {
  if (!message.value.trim()) return
  
  const userMessage = message.value.trim()
  message.value = ''
  
  try {
    await sendChatMessage(
      userMessage,
      chatControls.value as ChatControlsType
    )
    // Scroll to bottom after sending message
    scrollToBottom(chatMessagesRef.value)
  } catch (error) {
    console.error('Failed to send message:', error)
  }
}

function toggleMarkdown() {
  enableMarkdown.value = !enableMarkdown.value
}


// Clear chat history
function handleClearChat() {
  if (confirm('Are you sure you want to clear this conversation? This will permanently delete all messages and cannot be undone.')) {
    clearChat()
  }
}

// Clear memories
function handleClearMemories() {
  if (confirm('Are you sure you want to clear all memories for this conversation? This will permanently delete all compressed memories and cannot be undone.')) {
    clearMemories()
  }
}

// Message editing functions are now provided by useMessageActions composable

// Enhanced functions that add UI behavior
async function handleStartEditMessage(messageId: string) {
  startEditMessage(messageId, messages.value)
  // Expand thinking if it exists to show in edit mode
  const msg = messages.value.find(m => m.id === messageId)
  if (msg?.thinking) {
    expandedThinking.value.add(messageId)
  }
}

async function handleSaveEditMessage() {
  try {
    await saveEditMessage()
  } catch (error) {
    alert(error instanceof Error ? error.message : 'Failed to update message. Please try again.')
  }
}

async function handleDeleteMessage(messageId: string) {
  if (!confirm('Are you sure you want to delete this message?')) {
    return
  }
  
  try {
    await deleteMessage(messageId)
  } catch (error) {
    alert(error instanceof Error ? error.message : 'Failed to delete message. Please try again.')
  }
}


// Handle stop button click
async function handleStopChat() {
  if (!currentSessionId.value || isSessionCancelling.value) {
    return
  }
  
  try {
    console.log('Stopping chat session:', currentSessionId.value)
    const success = await cancelCurrentSession()
    if (success) {
      console.log('Chat session stopped successfully')
    } else {
      console.warn('Failed to stop chat session')
    }
  } catch (error) {
    console.error('Error stopping chat session:', error)
  }
}
</script>

<template>
  <div class="main-chat">
    <!-- Chat messages area -->
    <div class="chat-content">
      <div ref="chatMessagesRef" class="chat-messages" :class="{ 'has-messages': hasMessages }">
        <!-- Chat messages using MessageDisplay component -->
        <MessageDisplay
          v-if="hasMessages"
          :messages="messages"
          :hasMessages="hasMessages"
          :isStreaming="isStreaming"
          :currentStreamingMessage="currentStreamingMessage"
          :currentStreamingThinking="currentStreamingThinking"
          :processingStage="processingStage"
          :stageMessage="stageMessage"
          :isProcessingAfter="isProcessingAfter"
          :enableMarkdown="enableMarkdown"
          :selectedPersona="selectedPersona"
          :provider="chatControls.provider"
          :editingMessageId="editingMessageId"
          v-model:editingContent="editingContent"
          v-model:editingThinking="editingThinking"
          @toggleThinking="toggleThinking"
          @startEditMessage="handleStartEditMessage"
          @cancelEditMessage="cancelEditMessage"
          @saveEditMessage="handleSaveEditMessage"
          @deleteMessage="handleDeleteMessage"
        />
        
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
    
    <!-- Chat Input Component -->
    <ChatInput
      v-model:message="message"
      v-model:showPanel="showPanel"
      v-model:panelType="panelType"
      :hasMessages="hasMessages"
      :isStreaming="isStreaming"
      :currentSessionId="currentSessionId"
      :isSessionCancelling="isSessionCancelling"
      :enableMarkdown="enableMarkdown"
      @sendMessage="handleSendMessage"
      @stopChat="handleStopChat"
      @clearChat="handleClearChat"
      @clearMemories="handleClearMemories"
      @toggleMarkdown="toggleMarkdown"
    />
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

/* ChatInput component now handles all input styling */

/* Removed multi-session UI elements */



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

/* Menu options styling now handled by ChatInput component */



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