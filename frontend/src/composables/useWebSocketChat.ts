/**
 * Composable for WebSocket-based chat with immediate cancellation support
 *
 * Replaces SSE streaming with WebSocket bidirectional communication,
 * enabling <100ms cancellation latency for AI inference.
 */

import { ref, onUnmounted, type Ref } from 'vue'
import type { ChatMessage, ChatRequest, ChatControls } from '@/types/chat'

// Shared WebSocket state
const ws = ref<WebSocket | null>(null)
const isConnected = ref(false)
const isConnecting = ref(false)
const isStreaming = ref(false)
const currentSessionId = ref<string | null>(null)
const currentStreamingMessage = ref('')
const currentStreamingThinking = ref('')
const processingStage = ref<string | null>(null)
const stageMessage = ref<string | null>(null)
const messageCompleted = ref(false)
const isProcessingAfter = ref(false) // Track background Stage 5 execution

// WebSocket connection configuration
const WS_RECONNECT_DELAY = 3000
const WS_MAX_RECONNECT_ATTEMPTS = 5
let reconnectAttempts = 0
let reconnectTimeout: number | null = null
let fatalErrorOccurred = false // Prevent reconnection after fatal errors

export function useWebSocketChat(
  messages: Ref<ChatMessage[]>,
  error: Ref<string | null>,
  currentConversation: Ref<any>,
  addUserMessage: (content: string) => Promise<ChatMessage>,
  addAssistantMessage: (content: string, metadata?: any, thinking?: string, inputTokens?: number, outputTokens?: number, persist?: boolean) => Promise<ChatMessage>,
  getFreshChatControls: () => ChatControls | null,
  getProviderSettings: (provider: string) => any,
  buildChatControls: (controls: ChatControls) => any
) {

  /**
   * Get WebSocket URL from current location
   */
  const getWebSocketUrl = (): string => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    // Use port 8000 for backend API
    const port = '8000'
    return `${protocol}//${host}:${port}/ws/chat`
  }

  /**
   * Connect to WebSocket server
   */
  const connect = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (ws.value?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      if (isConnecting.value) {
        reject(new Error('Connection already in progress'))
        return
      }

      isConnecting.value = true
      const wsUrl = getWebSocketUrl()
      console.log('🔌 Connecting to WebSocket:', wsUrl)

      try {
        const socket = new WebSocket(wsUrl)

        socket.onopen = () => {
          console.log('✅ WebSocket connected')
          ws.value = socket
          isConnected.value = true
          isConnecting.value = false
          reconnectAttempts = 0
          fatalErrorOccurred = false // Reset fatal error flag on successful connection
          resolve()
        }

        socket.onmessage = (event) => {
          handleMessage(event.data)
        }

        socket.onerror = (err) => {
          console.error('❌ WebSocket error:', err)
          isConnecting.value = false
          if (!isConnected.value) {
            reject(new Error('WebSocket connection failed'))
          }
        }

        socket.onclose = (event) => {
          console.log('🔌 WebSocket closed:', event.code, event.reason)
          isConnected.value = false
          isConnecting.value = false
          ws.value = null

          // Attempt reconnection if not intentional close and no fatal error
          if (event.code !== 1000 && !fatalErrorOccurred && reconnectAttempts < WS_MAX_RECONNECT_ATTEMPTS) {
            scheduleReconnect()
          } else if (fatalErrorOccurred) {
            console.log('🛑 Not reconnecting due to fatal error')
          }
        }

      } catch (err) {
        console.error('❌ WebSocket connection error:', err)
        isConnecting.value = false
        reject(err)
      }
    })
  }

  /**
   * Schedule reconnection attempt
   */
  const scheduleReconnect = () => {
    if (reconnectTimeout) return

    reconnectAttempts++
    console.log(`🔄 Scheduling reconnect attempt ${reconnectAttempts}/${WS_MAX_RECONNECT_ATTEMPTS}`)

    reconnectTimeout = window.setTimeout(() => {
      reconnectTimeout = null
      connect().catch((err) => {
        console.error('Reconnect failed:', err)
      })
    }, WS_RECONNECT_DELAY)
  }

  /**
   * Disconnect from WebSocket
   */
  const disconnect = () => {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }

    if (ws.value) {
      console.log('🔌 Disconnecting WebSocket')
      ws.value.close(1000, 'Client disconnect')
      ws.value = null
    }

    isConnected.value = false
    isConnecting.value = false
  }

  /**
   * Handle incoming WebSocket message
   */
  const handleMessage = (data: string) => {
    try {
      const message = JSON.parse(data)
      const messageType = message.type

      switch (messageType) {
        case 'session_start':
          handleSessionStart(message.data)
          break

        case 'chat_session_start':
          handleChatSessionStart(message.data)
          break

        case 'stage_update':
          handleStageUpdate(message.data)
          break

        case 'chunk':
          handleChunk(message.data)
          break

        case 'done':
          handleDone(message.data)
          break

        case 'post_response_complete':
          handlePostResponseComplete(message.data)
          break

        case 'cancelled':
          handleCancelled(message.data)
          break

        case 'error':
          handleError(message.data)
          break

        case 'pong':
          // Heartbeat response - ignore
          break

        default:
          console.warn('Unknown message type:', messageType)
      }

    } catch (err) {
      console.error('Error parsing WebSocket message:', err)
    }
  }

  /**
   * Handle session_start message (WebSocket connection established)
   */
  const handleSessionStart = (data: any) => {
    console.log('🆔 WebSocket session started:', data.session_id)
  }

  /**
   * Handle chat_session_start message (new chat message started)
   */
  const handleChatSessionStart = (data: any) => {
    const newId = data.chat_session_id
    currentSessionId.value = newId
  }

  /**
   * Handle stage_update message
   */
  const handleStageUpdate = (data: any) => {
    // POST_RESPONSE stages (thinking_after) run in background without UI
    if (data.stage === 'thinking_after') {
      isProcessingAfter.value = true // Mark that Stage 5 is running
      return
    }

    processingStage.value = data.stage
    stageMessage.value = data.message
  }

  /**
   * Handle chunk message (streaming content)
   */
  const handleChunk = (data: any) => {
    if (data.content) {
      currentStreamingMessage.value += data.content
    }

    if (data.thinking) {
      currentStreamingThinking.value = data.thinking
    }

    if (data.done) {
      messageCompleted.value = true
    }
  }

  /**
   * Handle done message (streaming complete)
   */
  const handleDone = async (data: any) => {
    isStreaming.value = false
    processingStage.value = null
    stageMessage.value = null

    // Save assistant message to database
    if (currentStreamingMessage.value.trim()) {
      const metadata = data.metadata || {}
      const inputTokens = metadata.prompt_tokens || metadata.input_tokens
      const outputTokens = metadata.completion_tokens || metadata.output_tokens

      await addAssistantMessage(
        currentStreamingMessage.value.trim(),
        metadata,
        currentStreamingThinking.value || undefined,
        inputTokens,
        outputTokens,
        true
      )
    }

    // Reset streaming state
    currentStreamingMessage.value = ''
    currentStreamingThinking.value = ''
    // DON'T clear currentSessionId here - Stage 5 might still be running!
    // It will be cleared in handlePostResponseComplete
    messageCompleted.value = false
  }

  /**
   * Handle post_response_complete message
   */
  const handlePostResponseComplete = (data: any) => {
    // Only clear flags if this completion is for the current session
    if (data.chat_session_id === currentSessionId.value) {
      isProcessingAfter.value = false
      currentSessionId.value = null
    }
  }

  /**
   * Handle cancelled message
   */
  const handleCancelled = async (data: any) => {
    isStreaming.value = false
    isProcessingAfter.value = false
    processingStage.value = null
    stageMessage.value = null

    // Show cancellation message briefly
    error.value = data.message || '⏹️ Message generation was stopped'
    setTimeout(() => {
      if (error.value === data.message) {
        error.value = null
      }
    }, 3000)

    // Save partial response if any
    if (currentStreamingMessage.value.trim()) {
      // Save the accumulated message
      const partialMessage = currentStreamingMessage.value.trim()
      const partialThinking = currentStreamingThinking.value || undefined

      // Clear streaming state IMMEDIATELY to prevent duplicate display
      currentStreamingMessage.value = ''
      currentStreamingThinking.value = ''
      currentSessionId.value = null
      messageCompleted.value = false

      // Then save to messages (this adds to the permanent message list)
      await addAssistantMessage(
        partialMessage,
        { cancelled: true },
        partialThinking,
        undefined,
        undefined,
        true
      )
    } else {
      // No content to save, just reset state
      currentStreamingMessage.value = ''
      currentStreamingThinking.value = ''
      currentSessionId.value = null
      messageCompleted.value = false
    }
  }

  /**
   * Handle error message
   */
  const handleError = (data: any) => {
    console.error('❌ WebSocket error:', data.error)

    error.value = data.error || 'An error occurred'
    isStreaming.value = false
    isProcessingAfter.value = false
    processingStage.value = null
    stageMessage.value = null

    // Reset streaming state
    currentStreamingMessage.value = ''
    currentStreamingThinking.value = ''
    currentSessionId.value = null
    messageCompleted.value = false

    // If it's a fatal error (like import errors), don't auto-reconnect
    const fatalErrors = ['ModuleNotFoundError', 'ImportError', 'No module named', 'cannot import name']
    const isFatal = fatalErrors.some(errType => data.error && data.error.includes(errType))

    if (isFatal) {
      console.error('🛑 Fatal error detected - stopping auto-reconnection')
      fatalErrorOccurred = true // Set flag to prevent reconnection
      reconnectAttempts = WS_MAX_RECONNECT_ATTEMPTS // Prevent reconnection
      disconnect()
    }
  }

  /**
   * Send chat message via WebSocket
   */
  const sendMessageWebSocket = async (
    userMessage: string,
    chatControls: ChatControls
  ): Promise<void> => {
    // Ensure connected
    if (!isConnected.value) {
      await connect()
    }

    // If already streaming OR Stage 5 is running, cancel current session first
    if ((isStreaming.value || isProcessingAfter.value) && currentSessionId.value) {
      await cancelSession(currentSessionId.value)
      // Wait a bit for cancellation to complete
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    error.value = null
    isStreaming.value = true
    currentStreamingMessage.value = ''
    currentStreamingThinking.value = ''
    messageCompleted.value = false
    processingStage.value = 'thinking'
    stageMessage.value = 'Thinking...'

    // Set a temporary session ID immediately so cancel button is enabled
    // This will be replaced with the actual chat session ID when backend responds
    currentSessionId.value = 'pending'

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

      // Build chat message payload
      const chatMessage = {
        type: 'chat',
        data: {
          message: userMessage,
          provider: freshControls.provider,
          provider_settings: enhancedProviderSettings,
          chat_controls: buildChatControls(freshControls),
          persona_id: selectedPersonaId || undefined,
          conversation_id: currentConversation.value?.id || undefined
        }
      }

      // Send via WebSocket
      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify(chatMessage))
      } else {
        throw new Error('WebSocket not connected')
      }

    } catch (err: any) {
      console.error('Error sending WebSocket message:', err)
      error.value = err.message || 'Failed to send message'
      isStreaming.value = false
      processingStage.value = null
      stageMessage.value = null
    }
  }

  /**
   * Cancel current session
   */
  const cancelSession = async (sessionId: string): Promise<boolean> => {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      console.warn('Cannot cancel - WebSocket not connected')
      return false
    }

    try {
      const cancelMessage = {
        type: 'cancel',
        session_id: sessionId
      }

      ws.value.send(JSON.stringify(cancelMessage))
      return true

    } catch (err) {
      console.error('Error sending cancel:', err)
      return false
    }
  }

  /**
   * Cancel current session (public API)
   */
  const cancelCurrentSession = async (): Promise<boolean> => {
    if (!currentSessionId.value) {
      console.warn('No active session to cancel')
      return false
    }

    // If session ID is still 'pending', wait briefly for real ID
    if (currentSessionId.value === 'pending') {
      console.log('Waiting for chat session ID...')
      // Wait up to 500ms for the real session ID
      for (let i = 0; i < 50; i++) {
        await new Promise(resolve => setTimeout(resolve, 10))
        if (currentSessionId.value !== 'pending') {
          break
        }
      }

      // If still pending after wait, session hasn't started yet
      if (currentSessionId.value === 'pending') {
        console.warn('Chat session ID not received yet, cannot cancel')
        return false
      }
    }

    return await cancelSession(currentSessionId.value)
  }

  /**
   * Send ping to keep connection alive
   */
  const sendPing = () => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type: 'ping' }))
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    // Connection state
    isConnected,
    isConnecting,

    // Streaming state
    isStreaming,
    currentStreamingMessage,
    currentStreamingThinking,
    processingStage,
    stageMessage,
    messageCompleted,
    currentSessionId,
    isProcessingAfter,

    // Methods
    connect,
    disconnect,
    sendMessageWebSocket,
    cancelCurrentSession,
    sendPing
  }
}
