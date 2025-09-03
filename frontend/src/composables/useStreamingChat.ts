/**
 * Composable for managing streaming chat functionality
 */

import { ref, type Ref } from 'vue'
import { useApiConfig } from './apiConfig'
import { usePersonas } from './usePersonas'
import { useDebug } from './useDebug'
import type { ChatMessage, ChatRequest, ChatControls } from '@/types/chat'

// Shared streaming state
const isStreaming = ref(false)
const currentStreamingMessage = ref('')
const currentStreamingThinking = ref('')
const processingStage = ref<string | null>(null)
const stageMessage = ref<string | null>(null)
const isProcessingAfter = ref(false)
const messageCompleted = ref(false)
const hideStreamingUI = ref(false)

export function useStreamingChat(
  messages: Ref<ChatMessage[]>,
  error: Ref<string | null>,
  currentConversation: Ref<any>,
  addUserMessage: (content: string) => Promise<ChatMessage>,
  addAssistantMessage: (content: string, metadata?: any, thinking?: string, inputTokens?: number, outputTokens?: number, persist?: boolean) => Promise<ChatMessage>,
  cancelCurrentSession: () => Promise<boolean>,
  extractSessionId: (response: Response) => string | null,
  startSession: (sessionId: string | null) => void,
  getFreshChatControls: () => ChatControls | null,
  getProviderSettings: (provider: string) => any,
  buildChatControls: (controls: ChatControls) => any
) {
  const { apiRequest } = useApiConfig()
  const { getPersonaById } = usePersonas()
  const { addDebugRecord } = useDebug()

  // Send message with streaming
  const sendMessageStreaming = async (
    userMessage: string, 
    chatControls: ChatControls
  ): Promise<void> => {
    // If already streaming, cancel current session first
    if (isStreaming.value) {
      console.log('Cancelling current session for new message')
      await cancelCurrentSession()
    }

    error.value = null
    isStreaming.value = true
    currentStreamingMessage.value = ''
    currentStreamingThinking.value = ''
    messageCompleted.value = false
    hideStreamingUI.value = false
    // Start with thinking stage immediately to show animation
    processingStage.value = 'thinking'
    stageMessage.value = 'Thinking...'

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
        stream: true,
        chat_controls: buildChatControls(freshControls),
        provider_settings: enhancedProviderSettings,
        persona_id: selectedPersonaId || undefined,
        conversation_id: currentConversation.value?.id || undefined
      }

      // Use the enhanced cancellation-aware endpoint
      const response = await apiRequest('/api/chat/stream', {
        method: 'POST',
        body: JSON.stringify(chatRequest)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail?.message || errorData.message || 'Chat request failed')
      }

      // Extract and track session ID
      const sessionId = extractSessionId(response)
      if (sessionId) {
        startSession(sessionId)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('Failed to get response stream')

      const debugDataToRecord = await processStream(reader, selectedPersonaId)

      // Record debug data after successful streaming
      if (debugDataToRecord) {
        const persona = selectedPersonaId ? getPersonaById(selectedPersonaId) : null
        addDebugRecord({
          debugData: debugDataToRecord,
          personaName: persona?.name,
          personaId: selectedPersonaId || undefined,
          responseTime: (debugDataToRecord.response_timestamp - debugDataToRecord.request_timestamp)
        })
      }
    } catch (err) {
      await handleStreamingError(err)
    }
  }

  // Process streaming data from response
  const processStream = async (reader: ReadableStreamDefaultReader, selectedPersonaId: string | null): Promise<any> => {
    const decoder = new TextDecoder()
    let buffer = ''
    let firstChunk = true
    let debugDataToRecord: any = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (!data) continue

          try {
            const chunk = JSON.parse(data)
            if (chunk.event_type === 'error') {
              console.error('Backend streaming error:', {
                error: chunk.event_data?.error || 'Unknown error',
                session_id: chunk.event_data?.session_id
              })
            }
            const chunkDebugData = await processStreamChunk(chunk, firstChunk, selectedPersonaId)
            if (chunkDebugData) {
              debugDataToRecord = chunkDebugData
            }
            if (firstChunk && chunk.event_type === 'chunk') {
              firstChunk = false
            }
          } catch (parseError) {
            console.warn('Failed to parse streaming chunk:', data, parseError)
          }
        }
      }
    }

    return debugDataToRecord
  }

  // Process individual stream chunks
  const processStreamChunk = async (chunk: any, firstChunk: boolean, selectedPersonaId: string | null): Promise<any> => {
    if (chunk.error_type) {
      throw new Error(chunk.message || 'Streaming error')
    }

    switch (chunk.event_type) {
      case 'cancelled':
        await handleCancellation()
        return null
      case 'stage_update':
        handleStageUpdate(chunk)
        break
      case 'chunk':
        return await handleContentChunk(chunk, firstChunk, selectedPersonaId)
      case 'after_module_result':
        // AFTER module results can be used for debugging if needed
        break
      case 'done':
        handleStreamComplete()
        break
    }
    return null
  }

  // Handle stream cancellation
  const handleCancellation = async () => {
    console.log('Stream cancelled by server')
    resetStreamingState()
    await addAssistantMessage('⏹️ Message generation was stopped.', undefined, undefined, undefined, undefined, false)
  }

  // Handle processing stage updates
  const handleStageUpdate = (chunk: any) => {
    if (chunk.processing_stage === 'thinking_before') {
      processingStage.value = 'thinking'
      stageMessage.value = 'Thinking...'
    } else if (chunk.processing_stage === 'generating') {
      processingStage.value = 'thinking'
      stageMessage.value = 'Thinking...'
    } else if (chunk.processing_stage === 'thinking_after') {
      processingStage.value = 'thinking'
      stageMessage.value = 'Thinking...'
      currentStreamingMessage.value = ''
      currentStreamingThinking.value = ''
      isProcessingAfter.value = true
    }
  }

  // Handle content chunks
  const handleContentChunk = async (chunk: any, firstChunk: boolean, selectedPersonaId: string | null): Promise<any> => {
    if (firstChunk) {
      processingStage.value = 'generating'
      stageMessage.value = 'Generating...'
    }
    
    if (chunk.content) {
      currentStreamingMessage.value += chunk.content
    }
    if (chunk.thinking) {
      currentStreamingThinking.value += chunk.thinking
    }
    
    if (chunk.done) {
      
      let debugDataToReturn: any = null
      
      // Use debug_data from backend if available
      if (chunk.debug_data) {
        debugDataToReturn = {
          provider_request: chunk.debug_data.provider_request,
          provider_response: chunk.debug_data.provider_response,
          request_timestamp: chunk.debug_data.request_timestamp,
          response_timestamp: chunk.debug_data.response_timestamp
        }
      }
      
      // Clear streaming content and save message
      const savedContent = currentStreamingMessage.value
      const savedThinking = currentStreamingThinking.value
      
      resetStreamingContent()
      hideStreamingUI.value = true
      messageCompleted.value = true
      isProcessingAfter.value = true
      
      await addAssistantMessage(
        savedContent,
        chunk.metadata,
        savedThinking || undefined,
        chunk.metadata?.input_tokens,
        chunk.metadata?.output_tokens
      )
      
      return debugDataToReturn
    }
    
    return null
  }

  // Handle stream completion
  const handleStreamComplete = () => {
    isStreaming.value = false
    isProcessingAfter.value = false
    messageCompleted.value = false
    hideStreamingUI.value = false
    resetStreamingContent()
    console.log('Completed streaming session')
  }

  // Handle streaming errors
  const handleStreamingError = async (err: any) => {
    const message = err instanceof Error ? err.message : 'Unknown error occurred'
    error.value = message
    console.error('Chat streaming error:', err)
    await addAssistantMessage(`❌ Error: ${message}`, undefined, undefined, undefined, undefined, false)
    resetStreamingState()
  }

  // Reset streaming content
  const resetStreamingContent = () => {
    currentStreamingMessage.value = ''
    currentStreamingThinking.value = ''
    processingStage.value = null
    stageMessage.value = null
  }

  // Reset all streaming state
  const resetStreamingState = () => {
    isStreaming.value = false
    resetStreamingContent()
    isProcessingAfter.value = false
    messageCompleted.value = false
    hideStreamingUI.value = false
  }

  return {
    // State
    isStreaming,
    currentStreamingMessage,
    currentStreamingThinking,
    processingStage,
    stageMessage,
    isProcessingAfter,
    messageCompleted,
    hideStreamingUI,
    
    // Methods
    sendMessageStreaming,
    resetStreamingState,
    resetStreamingContent
  }
}