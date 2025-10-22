/**
 * Composable for managing chat functionality - WebSocket-only version
 */

import { ref, computed } from 'vue'
import { useApiConfig } from './apiConfig'
import { useConversationPersistence } from './useConversationPersistence'
import { useWebSocketChat } from './useWebSocketChat'

// Re-export types from centralized location
export type {
  ChatMessage,
  Conversation,
  ChatRequest,
  ChatControls,
  ProcessingStage,
  ChatProvider,
  MessageRole
} from '@/types/chat'

import type { ChatMessage, ChatControls } from '@/types/chat'

// Core chat state
const messages = ref<ChatMessage[]>([])
const error = ref<string | null>(null)

export function useChat() {
  const { apiRequest } = useApiConfig()

  // Initialize sub-composables
  const conversationPersistence = useConversationPersistence(messages, error)

  // Helper functions needed by WebSocket composable
  const getFreshChatControls = (): ChatControls | null => {
    try {
      const stored = localStorage.getItem('chat-controls')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  }

  const getProviderSettings = (provider: string) => {
    try {
      const key = `${provider}-connection`
      const stored = localStorage.getItem(key)
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  }

  const buildChatControls = (controls: ChatControls) => ({
    temperature: controls.temperature,
    max_tokens: controls.max_tokens,
    top_p: controls.top_p,
    frequency_penalty: controls.frequency_penalty,
    presence_penalty: controls.presence_penalty,
    stop_sequences: controls.stop_sequences || [],
    seed: controls.seed,
    repeat_penalty: controls.repeat_penalty,
    top_k: controls.top_k,
    response_format: controls.response_format,
    tool_choice: controls.tool_choice,
    parallel_tool_calls: controls.parallel_tool_calls
  })

  // Generate unique ID for messages
  const generateMessageId = () => `msg_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`

  // Add user message to chat
  const addUserMessage = async (content: string, persist: boolean = true): Promise<ChatMessage> => {
    const message: ChatMessage = {
      id: generateMessageId(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now()
    }

    messages.value.push(message)

    if (persist && conversationPersistence.currentConversation.value) {
      try {
        const savedMessage = await conversationPersistence.saveMessageToDb(message)
        // Update local message with saved data
        const index = messages.value.findIndex(m => m.id === message.id)
        if (index !== -1) {
          messages.value[index] = savedMessage
        }
      } catch (err) {
        console.error('Failed to save user message:', err)
      }
    }

    return message
  }

  // Add assistant message to chat
  const addAssistantMessage = async (
    content: string,
    metadata?: any,
    thinking?: string,
    inputTokens?: number,
    outputTokens?: number,
    persist: boolean = true
  ): Promise<ChatMessage> => {
    const message: ChatMessage = {
      id: generateMessageId(),
      role: 'assistant',
      content: content.trim(),
      timestamp: Date.now(),
      thinking,
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      metadata
    }

    messages.value.push(message)

    if (persist && conversationPersistence.currentConversation.value) {
      try {
        const savedMessage = await conversationPersistence.saveMessageToDb(message)
        const index = messages.value.findIndex(m => m.id === message.id)
        if (index !== -1) {
          messages.value[index] = savedMessage
        }
      } catch (err) {
        console.error('Failed to save assistant message:', err)
      }
    }

    return message
  }

  // Initialize WebSocket chat composable
  const webSocketChat = useWebSocketChat(
    messages,
    error,
    conversationPersistence.currentConversation,
    addUserMessage,
    addAssistantMessage,
    getFreshChatControls,
    getProviderSettings,
    buildChatControls
  )

  // Send chat message via WebSocket
  const sendChatMessage = async (
    userMessage: string,
    chatControls: ChatControls
  ): Promise<void> => {
    await webSocketChat.sendMessageWebSocket(userMessage, chatControls)
  }

  // Clear chat history
  const clearChat = async (clearFromDb: boolean = true) => {
    messages.value = []
    error.value = null

    if (clearFromDb && conversationPersistence.currentConversation.value) {
      await conversationPersistence.clearConversationInDb()
    }
  }

  // Clear memories for current conversation
  const clearMemories = async () => {
    if (!conversationPersistence.currentConversation.value) {
      console.warn('No active conversation to clear memories from')
      return
    }

    try {
      const response = await apiRequest(`/api/conversations/${conversationPersistence.currentConversation.value.id}/memories`, {
        method: 'DELETE'
      })

      if (response.ok) {
        console.log('Memories cleared successfully')
      } else {
        console.error('Failed to clear memories:', response.statusText)
      }
    } catch (error) {
      console.error('Error clearing memories:', error)
    }
  }

  // Remove a specific message
  const removeMessage = async (messageId: string, removeFromDb: boolean = true) => {
    const index = messages.value.findIndex(m => m.id === messageId)
    if (index === -1) {
      console.warn(`Message with ID ${messageId} not found`)
      return
    }

    messages.value.splice(index, 1)

    if (removeFromDb) {
      try {
        await conversationPersistence.deleteMessageFromDb(messageId)
      } catch (err) {
        console.error('Failed to remove message from database:', err)
      }
    }
  }

  // Update message content
  const updateMessage = async (messageId: string, updates: Partial<ChatMessage>) => {
    const index = messages.value.findIndex(m => m.id === messageId)
    if (index === -1) {
      console.warn(`Message with ID ${messageId} not found`)
      return
    }

    // Update local message
    Object.assign(messages.value[index], updates)

    // Update in database
    try {
      await conversationPersistence.updateMessageInDb(messageId, updates)
    } catch (err) {
      console.error('Failed to update message in database:', err)
    }
  }

  // Computed values
  const chatHistory = computed(() => messages.value)
  const hasMessages = computed(() => messages.value.length > 0)

  return {
    // State
    messages: chatHistory,
    isStreaming: computed(() => webSocketChat.isStreaming.value),
    currentStreamingMessage: computed(() => webSocketChat.currentStreamingMessage.value),
    currentStreamingThinking: computed(() => webSocketChat.currentStreamingThinking.value),
    error: computed(() => error.value),
    hasMessages,
    processingStage: computed(() => webSocketChat.processingStage.value),
    stageMessage: computed(() => webSocketChat.stageMessage.value),
    isProcessingAfter: computed(() => webSocketChat.isProcessingAfter.value),
    messageCompleted: computed(() => webSocketChat.messageCompleted.value),

    // Session management (WebSocket-only)
    currentSessionId: computed(() => webSocketChat.currentSessionId.value),
    cancelCurrentSession: webSocketChat.cancelCurrentSession,
    isSessionCancelling: ref(false), // Placeholder for compatibility

    // WebSocket connection
    isWebSocketConnected: webSocketChat.isConnected,
    isWebSocketConnecting: webSocketChat.isConnecting,
    connectWebSocket: webSocketChat.connect,
    disconnectWebSocket: webSocketChat.disconnect,

    // Conversation persistence
    currentConversation: conversationPersistence.currentConversation,
    isLoadingConversation: conversationPersistence.isLoadingConversation,
    loadConversationForPersona: conversationPersistence.loadConversationForPersona,

    // Chat methods
    sendChatMessage,
    clearChat,
    clearMemories,
    removeMessage,
    updateMessage,
    addUserMessage,
    addAssistantMessage
  }
}
