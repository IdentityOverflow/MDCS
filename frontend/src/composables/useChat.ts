/**
 * Composable for managing chat functionality - Streamlined version
 * Large functionality has been extracted to separate composables
 */

import { ref, computed } from 'vue'
import { useApiConfig } from './apiConfig'
import { usePersonas } from './usePersonas'
import { useDebug } from './useDebug'
import { useConversationPersistence } from './useConversationPersistence'
import { useSessionManagement } from './useSessionManagement'
import { useStreamingChat } from './useStreamingChat'

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

import type { ChatMessage, ChatControls, ChatRequest } from '@/types/chat'

// Core chat state
const messages = ref<ChatMessage[]>([])
const error = ref<string | null>(null)

export function useChat() {
  const { apiRequest } = useApiConfig()
  const { getPersonaById } = usePersonas()
  const { addDebugRecord } = useDebug()

  // Initialize sub-composables
  const conversationPersistence = useConversationPersistence(messages, error)
  
  const sessionManagement = useSessionManagement(
    ref(false), // isStreaming - will be overridden by streaming composable
    ref(null),  // processingStage
    ref(null),  // stageMessage  
    ref(''),    // currentStreamingMessage
    ref('')     // currentStreamingThinking
  )

  // Helper functions needed by streaming composable
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

  // Initialize streaming composable with required dependencies
  const streamingChat = useStreamingChat(
    messages,
    error,
    conversationPersistence.currentConversation,
    addUserMessage,
    addAssistantMessage,
    sessionManagement.cancelCurrentSession,
    sessionManagement.extractSessionId,
    sessionManagement.startSession,
    getFreshChatControls,
    getProviderSettings,
    buildChatControls
  )

  // Send message without streaming
  const sendMessage = async (
    userMessage: string,
    chatControls: ChatControls
  ): Promise<void> => {
    // If already streaming, cancel current session first
    if (streamingChat.isStreaming.value) {
      await sessionManagement.cancelCurrentSession()
    }

    error.value = null
    streamingChat.isStreaming.value = true
    streamingChat.processingStage.value = 'thinking'
    streamingChat.stageMessage.value = 'Thinking...'

    await addUserMessage(userMessage)

    try {
      const freshControls = getFreshChatControls() || chatControls
      const providerSettings = getProviderSettings(freshControls.provider)
      
      if (!providerSettings) {
        throw new Error(`${freshControls.provider.toUpperCase()} connection settings not found.`)
      }

      const selectedPersonaId = localStorage.getItem('selectedPersonaId')
      const enhancedProviderSettings = {
        ...providerSettings,
        model: freshControls.selected_model || providerSettings.default_model
      }

      const chatRequest: ChatRequest = {
        message: userMessage,
        provider: freshControls.provider,
        stream: false,
        chat_controls: buildChatControls(freshControls),
        provider_settings: enhancedProviderSettings,
        persona_id: selectedPersonaId || undefined,
        conversation_id: conversationPersistence.currentConversation.value?.id || undefined
      }

      const response = await apiRequest('/api/chat/send', {
        method: 'POST',
        body: JSON.stringify(chatRequest)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail?.message || errorData.message || 'Chat request failed')
      }

      const result = await response.json()
      
      await addAssistantMessage(
        result.content,
        result.metadata,
        result.thinking,
        result.metadata?.input_tokens,
        result.metadata?.output_tokens
      )

      // Record debug data if available
      if (result.debug_data) {
        const persona = selectedPersonaId ? getPersonaById(selectedPersonaId) : null
        addDebugRecord({
          debugData: result.debug_data,
          personaName: persona?.name,
          personaId: selectedPersonaId || undefined,
          responseTime: result.debug_data.response_timestamp - result.debug_data.request_timestamp
        })
      }

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred'
      error.value = message
      console.error('Chat error:', err)
      await addAssistantMessage(`❌ Error: ${message}`, undefined, undefined, undefined, undefined, false)
    } finally {
      streamingChat.isStreaming.value = false
      streamingChat.processingStage.value = null
      streamingChat.stageMessage.value = null
    }
  }

  // Main send function that chooses streaming or non-streaming
  const sendChatMessage = async (
    userMessage: string,
    chatControls: ChatControls,
    _personaTemplate?: string
  ): Promise<void> => {
    if (chatControls.stream) {
      await streamingChat.sendMessageStreaming(userMessage, chatControls)
    } else {
      await sendMessage(userMessage, chatControls)
    }
  }

  // Clear chat history
  const clearChat = async (clearFromDb: boolean = true) => {
    messages.value = []
    streamingChat.resetStreamingContent()
    error.value = null
    
    if (clearFromDb && conversationPersistence.currentConversation.value) {
      await conversationPersistence.clearConversationInDb()
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
  const isLoading = computed(() => streamingChat.isStreaming.value)

  return {
    // State
    messages: chatHistory,
    isStreaming: isLoading,
    currentStreamingMessage: computed(() => streamingChat.currentStreamingMessage.value),
    currentStreamingThinking: computed(() => streamingChat.currentStreamingThinking.value),
    error: computed(() => error.value),
    hasMessages,
    processingStage: computed(() => streamingChat.processingStage.value),
    stageMessage: computed(() => streamingChat.stageMessage.value),
    isProcessingAfter: computed(() => streamingChat.isProcessingAfter.value),
    messageCompleted: computed(() => streamingChat.messageCompleted.value),
    hideStreamingUI: computed(() => streamingChat.hideStreamingUI.value),
    
    // Session management
    currentSessionId: sessionManagement.currentSessionId,
    cancelCurrentSession: sessionManagement.cancelCurrentSession,
    isSessionCancelling: sessionManagement.isSessionCancelling,
    
    // Conversation persistence
    currentConversation: conversationPersistence.currentConversation,
    isLoadingConversation: conversationPersistence.isLoadingConversation,
    loadConversationForPersona: conversationPersistence.loadConversationForPersona,
    
    // Chat methods
    sendChatMessage,
    clearChat,
    removeMessage,
    updateMessage,
    addUserMessage,
    addAssistantMessage
  }
}