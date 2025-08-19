/**
 * Composable for managing chat functionality
 */

import { ref, computed, type Ref } from 'vue'
import { useApiConfig } from './apiConfig'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  metadata?: {
    model?: string
    provider?: string
    tokens_used?: number
    response_time?: number
  }
}

export interface ChatRequest {
  message: string
  provider: 'ollama' | 'openai'
  stream: boolean
  chat_controls: Record<string, any>
  provider_settings?: Record<string, any>
}

export interface ChatControls {
  provider: 'ollama' | 'openai'
  selectedPersonaId: string
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
const error = ref<string | null>(null)

export function useChat() {
  const { apiRequest } = useApiConfig()
  
  // Computed values
  const chatHistory = computed(() => messages.value)
  const hasMessages = computed(() => messages.value.length > 0)
  const isLoading = computed(() => isStreaming.value)
  
  // Generate unique ID for messages
  const generateMessageId = () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  
  // Add user message to chat
  const addUserMessage = (content: string): ChatMessage => {
    const message: ChatMessage = {
      id: generateMessageId(),
      role: 'user',
      content,
      timestamp: Date.now()
    }
    messages.value.push(message)
    return message
  }
  
  // Add assistant message to chat
  const addAssistantMessage = (content: string, metadata?: ChatMessage['metadata']): ChatMessage => {
    const message: ChatMessage = {
      id: generateMessageId(),
      role: 'assistant',
      content,
      timestamp: Date.now(),
      metadata
    }
    messages.value.push(message)
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
  
  // Get provider settings from localStorage
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

  // Build chat controls from current settings and persona
  const buildChatControls = (chatControls: ChatControls, personaTemplate?: string): Record<string, any> => {
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
      // Ollama specific
      ollama_top_k: chatControls.ollama_top_k,
      ollama_repeat_penalty: chatControls.ollama_repeat_penalty,
      ollama_mirostat: chatControls.ollama_mirostat,
      ollama_num_ctx: chatControls.ollama_num_ctx,
      // OpenAI specific
      reasoning_effort: chatControls.reasoning_effort,
      verbosity: chatControls.verbosity
    }
    
    // Add system prompt from persona template if available
    if (personaTemplate && personaTemplate.trim()) {
      controls.system_or_instructions = personaTemplate.trim()
    }
    
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
    
    // Add user message immediately
    addUserMessage(userMessage)
    
    try {
      // Get provider settings from localStorage
      const providerSettings = getProviderSettings(chatControls.provider)
      if (!providerSettings) {
        throw new Error(`${chatControls.provider.toUpperCase()} connection settings not found. Please configure in Settings.`)
      }

      const chatRequest: ChatRequest = {
        message: userMessage,
        provider: chatControls.provider,
        stream: true,
        chat_controls: buildChatControls(chatControls, personaTemplate),
        provider_settings: providerSettings
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
      let assistantMessage: ChatMessage | null = null
      
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
                  
                  // If this is the final chunk, save the complete message
                  if (chunk.done) {
                    assistantMessage = addAssistantMessage(
                      currentStreamingMessage.value,
                      chunk.metadata
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
      addAssistantMessage(`❌ Error: ${message}`)
    } finally {
      isStreaming.value = false
      currentStreamingMessage.value = ''
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
    addUserMessage(userMessage)
    
    try {
      // Get provider settings from localStorage
      const providerSettings = getProviderSettings(chatControls.provider)
      if (!providerSettings) {
        throw new Error(`${chatControls.provider.toUpperCase()} connection settings not found. Please configure in Settings.`)
      }

      const chatRequest: ChatRequest = {
        message: userMessage,
        provider: chatControls.provider,
        stream: false,
        chat_controls: buildChatControls(chatControls, personaTemplate),
        provider_settings: providerSettings
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
      
      // Add assistant response
      addAssistantMessage(data.content, data.metadata)
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred'
      error.value = message
      console.error('Chat error:', err)
      
      // Add error message as assistant message
      addAssistantMessage(`❌ Error: ${message}`)
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
  
  // Clear chat history
  const clearChat = () => {
    messages.value = []
    currentStreamingMessage.value = ''
    error.value = null
  }
  
  // Remove a specific message
  const removeMessage = (messageId: string) => {
    const index = messages.value.findIndex(m => m.id === messageId)
    if (index >= 0) {
      messages.value.splice(index, 1)
    }
  }
  
  return {
    // State
    messages: chatHistory,
    isStreaming: isLoading,
    currentStreamingMessage: computed(() => currentStreamingMessage.value),
    error: computed(() => error.value),
    
    // Computed
    hasMessages,
    
    // Methods
    sendChatMessage,
    clearChat,
    removeMessage,
    addUserMessage,
    addAssistantMessage,
    addSystemMessage
  }
}