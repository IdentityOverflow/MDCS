/**
 * Composable for managing chat functionality
 */

import { ref, computed, type Ref } from 'vue'
import { useApiConfig } from './apiConfig'
import { usePersonas } from './usePersonas'
import { useDebug } from './useDebug'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  thinking?: string
  metadata?: {
    model?: string
    provider?: string
    tokens_used?: number
    response_time?: number
  }
  // Additional fields for persistence
  conversation_id?: string
  input_tokens?: number
  output_tokens?: number
  extra_data?: Record<string, any>
  created_at?: string
  updated_at?: string
}

export interface Conversation {
  id: string
  title: string
  persona_id?: string
  provider_type?: string
  provider_config?: Record<string, any>
  messages: ChatMessage[]
  created_at: string
  updated_at: string
}

export interface ChatRequest {
  message: string
  provider: 'ollama' | 'openai'
  stream: boolean
  chat_controls: Record<string, any>
  provider_settings?: Record<string, any>
  persona_id?: string
}

export interface ChatControls {
  provider: 'ollama' | 'openai'
  selected_model: string
  temperature: number
  top_p: number
  max_tokens: number
  presence_penalty: number
  frequency_penalty: number
  seed: number | null
  stop: string[]
  json_mode: string
  tools: any[]
  tool_choice: string
  stream: boolean
  thinking_enabled: boolean
  // Ollama specific
  ollama_top_k: number
  ollama_repeat_penalty: number
  ollama_mirostat: number
  ollama_num_ctx: number
  // OpenAI specific
  reasoning_effort: string
  verbosity: string
}

// Global chat state
const messages: Ref<ChatMessage[]> = ref([])
const isStreaming = ref(false)
const currentStreamingMessage = ref('')
const currentStreamingThinking = ref('')
const error = ref<string | null>(null)

// Conversation persistence state
const currentConversation: Ref<Conversation | null> = ref(null)
const isLoadingConversation = ref(false)
const isSavingMessage = ref(false)

export function useChat() {
  const { apiRequest } = useApiConfig()
  const { getPersonaById } = usePersonas()
  const { addDebugRecord } = useDebug()
  
  // Computed values
  const chatHistory = computed(() => messages.value)
  const hasMessages = computed(() => messages.value.length > 0)
  const isLoading = computed(() => isStreaming.value)
  
  // Generate unique ID for messages (fallback for local messages)
  const generateMessageId = () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  // === CONVERSATION PERSISTENCE FUNCTIONS ===
  
  // Load conversation for a persona
  const loadConversationForPersona = async (personaId: string): Promise<void> => {
    isLoadingConversation.value = true
    error.value = null
    
    try {
      const response = await apiRequest(`/api/conversations/by-persona/${personaId}`)
      
      if (response.ok) {
        const conversation: Conversation = await response.json()
        currentConversation.value = conversation
        
        // Convert API messages to chat messages format
        messages.value = conversation.messages.map(msg => ({
          id: msg.id,
          role: msg.role as 'user' | 'assistant' | 'system',
          content: msg.content,
          timestamp: new Date(msg.created_at || Date.now()).getTime(),
          thinking: msg.thinking || undefined,
          conversation_id: conversation.id,
          input_tokens: msg.input_tokens || undefined,
          output_tokens: msg.output_tokens || undefined,
          extra_data: msg.extra_data || undefined,
          metadata: msg.extra_data?.metadata || undefined
        }))
      } else if (response.status === 404) {
        // No existing conversation for this persona, create a new one
        await createConversationForPersona(personaId)
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to load conversation')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load conversation'
      error.value = message
      console.error('Load conversation error:', err)
    } finally {
      isLoadingConversation.value = false
    }
  }

  // Create new conversation for persona
  const createConversationForPersona = async (personaId: string): Promise<void> => {
    try {
      const persona = getPersonaById(personaId)
      const title = `Chat with ${persona?.name || 'AI'}`
      
      const response = await apiRequest('/api/conversations', {
        method: 'POST',
        body: JSON.stringify({
          title,
          persona_id: personaId,
          provider_type: null,
          provider_config: null
        })
      })

      if (response.ok) {
        const conversation: Conversation = await response.json()
        currentConversation.value = conversation
        messages.value = [] // Start with empty conversation
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create conversation')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create conversation'
      error.value = message
      console.error('Create conversation error:', err)
    }
  }

  // Save message to database
  const saveMessageToDb = async (message: ChatMessage): Promise<ChatMessage> => {
    if (!currentConversation.value) {
      throw new Error('No active conversation')
    }

    try {
      const response = await apiRequest('/api/messages', {
        method: 'POST',
        body: JSON.stringify({
          conversation_id: currentConversation.value.id,
          role: message.role,
          content: message.content,
          thinking: message.thinking || null,
          input_tokens: message.input_tokens || null,
          output_tokens: message.output_tokens || null,
          extra_data: message.extra_data || null
        })
      })

      if (response.ok) {
        const savedMessage = await response.json()
        // Return message with database ID
        return {
          ...message,
          id: savedMessage.id,
          conversation_id: savedMessage.conversation_id
        }
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to save message')
      }
    } catch (err) {
      console.error('Save message error:', err)
      throw err
    }
  }

  // Update message in database
  const updateMessageInDb = async (messageId: string, updates: Partial<ChatMessage>): Promise<void> => {
    try {
      const response = await apiRequest(`/api/messages/${messageId}`, {
        method: 'PUT',
        body: JSON.stringify({
          content: updates.content,
          thinking: updates.thinking,
          input_tokens: updates.input_tokens,
          output_tokens: updates.output_tokens,
          extra_data: updates.extra_data
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update message')
      }
    } catch (err) {
      console.error('Update message error:', err)
      throw err
    }
  }

  // Delete message from database
  const deleteMessageFromDb = async (messageId: string): Promise<void> => {
    try {
      const response = await apiRequest(`/api/messages/${messageId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to delete message')
      }
    } catch (err) {
      console.error('Delete message error:', err)
      throw err
    }
  }

  // Clear conversation in database
  const clearConversationInDb = async (): Promise<void> => {
    if (!currentConversation.value) return

    try {
      const response = await apiRequest(`/api/conversations/${currentConversation.value.id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Create a new conversation for the same persona
        if (currentConversation.value.persona_id) {
          await createConversationForPersona(currentConversation.value.persona_id)
        } else {
          currentConversation.value = null
        }
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to clear conversation')
      }
    } catch (err) {
      console.error('Clear conversation error:', err)
      throw err
    }
  }
  
  // Add user message to chat (with optional persistence)
  const addUserMessage = async (content: string, persist: boolean = true): Promise<ChatMessage> => {
    const message: ChatMessage = {
      id: generateMessageId(),
      role: 'user',
      content,
      timestamp: Date.now()
    }
    
    messages.value.push(message)
    
    // Save to database if persistence is enabled and we have an active conversation
    if (persist && currentConversation.value) {
      try {
        isSavingMessage.value = true
        const savedMessage = await saveMessageToDb(message)
        // Update the message in our local state with the database ID
        const index = messages.value.findIndex(m => m.id === message.id)
        if (index >= 0) {
          messages.value[index] = savedMessage
        }
        return savedMessage
      } catch (err) {
        console.error('Failed to save user message:', err)
        // Continue with local message even if persistence fails
        return message
      } finally {
        isSavingMessage.value = false
      }
    }
    
    return message
  }
  
  // Add assistant message to chat (with optional persistence)
  const addAssistantMessage = async (
    content: string, 
    metadata?: ChatMessage['metadata'], 
    thinking?: string,
    inputTokens?: number,
    outputTokens?: number,
    persist: boolean = true
  ): Promise<ChatMessage> => {
    const message: ChatMessage = {
      id: generateMessageId(),
      role: 'assistant',
      content,
      timestamp: Date.now(),
      thinking,
      metadata,
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      extra_data: metadata ? { metadata } : undefined
    }
    
    messages.value.push(message)
    
    // Save to database if persistence is enabled and we have an active conversation
    if (persist && currentConversation.value) {
      try {
        isSavingMessage.value = true
        const savedMessage = await saveMessageToDb(message)
        // Update the message in our local state with the database ID
        const index = messages.value.findIndex(m => m.id === message.id)
        if (index >= 0) {
          messages.value[index] = savedMessage
        }
        return savedMessage
      } catch (err) {
        console.error('Failed to save assistant message:', err)
        // Continue with local message even if persistence fails
        return message
      } finally {
        isSavingMessage.value = false
      }
    }
    
    return message
  }
  
  // Add system message (for persona templates)
  const addSystemMessage = (content: string): ChatMessage => {
    const message: ChatMessage = {
      id: generateMessageId(),
      role: 'system',
      content,
      timestamp: Date.now()
    }
    // Insert system message at the beginning if no system message exists
    const existingSystemIndex = messages.value.findIndex(m => m.role === 'system')
    if (existingSystemIndex >= 0) {
      messages.value[existingSystemIndex] = message
    } else {
      messages.value.unshift(message)
    }
    return message
  }
  
  // Get provider settings from localStorage (always fresh)
  const getProviderSettings = (provider: 'ollama' | 'openai'): Record<string, any> | null => {
    try {
      if (provider === 'ollama') {
        const ollamaSettings = localStorage.getItem('ollama-connection')
        return ollamaSettings ? JSON.parse(ollamaSettings) : null
      } else if (provider === 'openai') {
        const openaiSettings = localStorage.getItem('openai-connection')
        return openaiSettings ? JSON.parse(openaiSettings) : null
      }
      return null
    } catch (error) {
      console.error(`Failed to load ${provider} settings from localStorage:`, error)
      return null
    }
  }

  // Get fresh chat controls from localStorage
  const getFreshChatControls = (): ChatControls | null => {
    try {
      const controlsData = localStorage.getItem('chat-controls')
      return controlsData ? JSON.parse(controlsData) : null
    } catch (error) {
      console.error('Failed to load chat controls from localStorage:', error)
      return null
    }
  }

  // Get selected persona template from localStorage
  const getSelectedPersonaTemplate = (): string | null => {
    try {
      const selectedPersonaId = localStorage.getItem('selectedPersonaId')
      if (selectedPersonaId) {
        const persona = getPersonaById(selectedPersonaId)
        return persona?.template || null
      }
      return null
    } catch (error) {
      console.error('Failed to get selected persona template:', error)
      return null
    }
  }

  // Build chat controls from current settings
  const buildChatControls = (chatControls: ChatControls): Record<string, any> => {
    const controls: Record<string, any> = {
      temperature: chatControls.temperature,
      top_p: chatControls.top_p,
      max_tokens: chatControls.max_tokens,
      presence_penalty: chatControls.presence_penalty,
      frequency_penalty: chatControls.frequency_penalty,
      seed: chatControls.seed,
      stop: chatControls.stop,
      json_mode: chatControls.json_mode,
      tools: chatControls.tools,
      tool_choice: chatControls.tool_choice,
      stream: chatControls.stream,
      thinking_enabled: chatControls.thinking_enabled,
      // Ollama specific
      ollama_top_k: chatControls.ollama_top_k,
      ollama_repeat_penalty: chatControls.ollama_repeat_penalty,
      ollama_mirostat: chatControls.ollama_mirostat,
      ollama_num_ctx: chatControls.ollama_num_ctx,
      // OpenAI specific
      reasoning_effort: chatControls.reasoning_effort,
      verbosity: chatControls.verbosity
    }
    
    // Note: System prompt now comes from persona_id resolution on the backend
    return controls
  }
  
  // Send message with streaming
  const sendMessageStreaming = async (
    userMessage: string, 
    chatControls: ChatControls,
    personaTemplate?: string
  ): Promise<void> => {
    if (isStreaming.value) return
    
    error.value = null
    isStreaming.value = true
    currentStreamingMessage.value = ''
    currentStreamingThinking.value = ''
    
    // Add user message immediately
    await addUserMessage(userMessage)
    
    try {
      // Get fresh chat controls from localStorage to ensure we have the latest values
      const freshControls = getFreshChatControls() || chatControls
      
      // Get provider settings from localStorage
      const providerSettings = getProviderSettings(freshControls.provider)
      if (!providerSettings) {
        throw new Error(`${freshControls.provider.toUpperCase()} connection settings not found. Please configure in Settings.`)
      }

      // Get selected persona ID for backend template resolution
      const selectedPersonaId = localStorage.getItem('selectedPersonaId')

      // Add selected model to provider settings
      const enhancedProviderSettings = {
        ...providerSettings,
        model: freshControls.selected_model || providerSettings.default_model
      }

      const chatRequest: ChatRequest = {
        message: userMessage,
        provider: freshControls.provider,
        stream: true,
        chat_controls: buildChatControls(freshControls),
        provider_settings: enhancedProviderSettings,
        persona_id: selectedPersonaId || undefined
      }

      
      const response = await apiRequest('/api/chat/stream', {
        method: 'POST',
        body: JSON.stringify(chatRequest)
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        const errorMessage = errorData.detail?.message || errorData.message || 'Chat request failed'
        throw new Error(errorMessage)
      }
      
      // Handle streaming response with EventSource-like parsing
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Failed to get response stream')
      }
      
      const decoder = new TextDecoder()
      let buffer = ''
      
      try {
        while (true) {
          const { done, value } = await reader.read()
          
          if (done) break
          
          buffer += decoder.decode(value, { stream: true })
          
          // Process complete lines
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // Keep incomplete line in buffer
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()
              
              if (data === '[DONE]') {
                break
              }
              
              if (data) {
                try {
                  const chunk = JSON.parse(data)
                  
                  if (chunk.error_type) {
                    throw new Error(chunk.message || 'Streaming error')
                  }
                  
                  // Add content to streaming message
                  currentStreamingMessage.value += chunk.content || ''
                  
                  // Add thinking content to streaming thinking if available
                  if (chunk.thinking) {
                    currentStreamingThinking.value += chunk.thinking
                  }
                  
                  // If this is the final chunk, save the complete message
                  if (chunk.done) {
                    // Capture debug data if available
                    if (chunk.debug_data) {
                      const personaName = selectedPersonaId ? getPersonaById(selectedPersonaId)?.name : undefined
                      addDebugRecord({
                        debugData: chunk.debug_data,
                        personaName,
                        personaId: selectedPersonaId || undefined,
                        resolvedSystemPrompt: chunk.resolved_system_prompt,
                        responseTime: chunk.metadata?.response_time
                      })
                    }
                    
                    await addAssistantMessage(
                      currentStreamingMessage.value,
                      chunk.metadata,
                      currentStreamingThinking.value || undefined,
                      chunk.metadata?.input_tokens,
                      chunk.metadata?.output_tokens
                    )
                  }
                } catch (parseError) {
                  console.warn('Failed to parse streaming chunk:', data)
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock()
      }
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred'
      error.value = message
      console.error('Chat streaming error:', err)
      
      // Add error message as assistant message
      await addAssistantMessage(`❌ Error: ${message}`, undefined, undefined, undefined, undefined, false)
    } finally {
      isStreaming.value = false
      currentStreamingMessage.value = ''
      currentStreamingThinking.value = ''
    }
  }
  
  // Send message without streaming
  const sendMessage = async (
    userMessage: string,
    chatControls: ChatControls,
    personaTemplate?: string
  ): Promise<void> => {
    if (isStreaming.value) return
    
    error.value = null
    isStreaming.value = true
    
    // Add user message immediately
    await addUserMessage(userMessage)
    
    try {
      // Get fresh chat controls from localStorage to ensure we have the latest values
      const freshControls = getFreshChatControls() || chatControls
      
      // Get provider settings from localStorage
      const providerSettings = getProviderSettings(freshControls.provider)
      if (!providerSettings) {
        throw new Error(`${freshControls.provider.toUpperCase()} connection settings not found. Please configure in Settings.`)
      }

      // Get selected persona ID for backend template resolution
      const selectedPersonaId = localStorage.getItem('selectedPersonaId')

      // Add selected model to provider settings
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
        persona_id: selectedPersonaId || undefined
      }

      
      const response = await apiRequest('/api/chat/send', {
        method: 'POST',
        body: JSON.stringify(chatRequest)
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        const errorMessage = errorData.detail?.message || errorData.message || 'Chat request failed'
        throw new Error(errorMessage)
      }
      
      const data = await response.json()
      
      // Capture debug data if available
      if (data.debug_data) {
        const personaName = selectedPersonaId ? getPersonaById(selectedPersonaId)?.name : undefined
        addDebugRecord({
          debugData: data.debug_data,
          personaName,
          personaId: selectedPersonaId || undefined,
          resolvedSystemPrompt: data.resolved_system_prompt,
          responseTime: data.metadata?.response_time
        })
      }
      
      // Add assistant response
      await addAssistantMessage(
        data.content, 
        data.metadata, 
        data.thinking || undefined,
        data.metadata?.input_tokens,
        data.metadata?.output_tokens
      )
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred'
      error.value = message
      console.error('Chat error:', err)
      
      // Add error message as assistant message
      await addAssistantMessage(`❌ Error: ${message}`, undefined, undefined, undefined, undefined, false)
    } finally {
      isStreaming.value = false
    }
  }
  
  // Main send function that chooses streaming or non-streaming
  const sendChatMessage = async (
    userMessage: string,
    chatControls: ChatControls,
    personaTemplate?: string
  ): Promise<void> => {
    if (chatControls.stream) {
      await sendMessageStreaming(userMessage, chatControls, personaTemplate)
    } else {
      await sendMessage(userMessage, chatControls, personaTemplate)
    }
  }
  
  // Clear chat history (with optional database clearing)
  const clearChat = async (clearFromDb: boolean = true) => {
    messages.value = []
    currentStreamingMessage.value = ''
    currentStreamingThinking.value = ''
    error.value = null
    
    // Clear from database if requested and we have an active conversation
    if (clearFromDb && currentConversation.value) {
      try {
        await clearConversationInDb()
      } catch (err) {
        console.error('Failed to clear conversation from database:', err)
        // Continue with local clear even if database clear fails
      }
    }
  }
  
  // Remove a specific message (with optional database removal)
  const removeMessage = async (messageId: string, removeFromDb: boolean = true) => {
    const index = messages.value.findIndex(m => m.id === messageId)
    if (index >= 0) {
      messages.value.splice(index, 1)
      
      // Remove from database if requested
      if (removeFromDb) {
        try {
          await deleteMessageFromDb(messageId)
        } catch (err) {
          console.error('Failed to remove message from database:', err)
          // Message was already removed locally, so don't re-add it
        }
      }
    }
  }
  
  // Update message content (with database sync)
  const updateMessage = async (messageId: string, updates: Partial<ChatMessage>) => {
    const index = messages.value.findIndex(m => m.id === messageId)
    if (index >= 0) {
      // Update local message
      messages.value[index] = { ...messages.value[index], ...updates }
      
      // Sync with database
      try {
        await updateMessageInDb(messageId, updates)
      } catch (err) {
        console.error('Failed to update message in database:', err)
        throw err
      }
    }
  }
  
  return {
    // State
    messages: chatHistory,
    isStreaming: isLoading,
    currentStreamingMessage: computed(() => currentStreamingMessage.value),
    currentStreamingThinking: computed(() => currentStreamingThinking.value),
    error: computed(() => error.value),
    
    // Conversation persistence state
    currentConversation: computed(() => currentConversation.value),
    isLoadingConversation: computed(() => isLoadingConversation.value),
    isSavingMessage: computed(() => isSavingMessage.value),
    
    // Computed
    hasMessages,
    
    // Chat methods
    sendChatMessage,
    clearChat,
    removeMessage,
    updateMessage,
    addUserMessage,
    addAssistantMessage,
    addSystemMessage,
    
    // Persistence methods
    loadConversationForPersona,
    createConversationForPersona
  }
}