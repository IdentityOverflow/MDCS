/**
 * Composable for managing chat session lifecycle and cancellation
 */

import { ref, type Ref } from 'vue'
import { useApiConfig } from './apiConfig'

// Shared session state
const currentSessionId = ref<string | null>(null)
const isSessionCancelling = ref(false)

export function useSessionManagement(
  isStreaming: Ref<boolean>,
  processingStage: Ref<string | null>,
  stageMessage: Ref<string | null>,
  currentStreamingMessage: Ref<string>,
  currentStreamingThinking: Ref<string>
) {
  const { apiRequest } = useApiConfig()

  // Cancel current session
  const cancelCurrentSession = async (): Promise<boolean> => {
    if (!currentSessionId.value || isSessionCancelling.value) {
      return false
    }

    isSessionCancelling.value = true
    
    try {
      // Use the new cancellation endpoints
      const response = await apiRequest(`/api/chat/cancel/${currentSessionId.value}`, {
        method: 'POST'
      })

      if (response.ok) {
        const result = await response.json()
        console.log('Session cancellation result:', result)
        
        // Clean up session state
        if (result.cancelled) {
          currentSessionId.value = null
          isStreaming.value = false
          processingStage.value = null
          stageMessage.value = null
          currentStreamingMessage.value = ''
          currentStreamingThinking.value = ''
        }
        
        return result.cancelled
      } else {
        console.error('Failed to cancel session:', response.statusText)
        return false
      }
    } catch (err) {
      console.error('Error cancelling session:', err)
      return false
    } finally {
      isSessionCancelling.value = false
    }
  }

  // Get session status
  const getSessionStatus = async (sessionId: string) => {
    try {
      const response = await apiRequest(`/api/chat/status/${sessionId}`)
      if (response.ok) {
        return await response.json()
      }
      return null
    } catch (err) {
      console.error('Error getting session status:', err)
      return null
    }
  }

  // Get all active sessions
  const getActiveSessions = async () => {
    try {
      const response = await apiRequest('/api/chat/sessions/active')
      if (response.ok) {
        const data = await response.json()
        return data.sessions || []
      }
      return []
    } catch (err) {
      console.error('Error getting active sessions:', err)
      return []
    }
  }

  // Extract session ID from response headers
  const extractSessionId = (response: Response): string | null => {
    return response.headers.get('X-Session-ID') || null
  }

  // Initialize new session
  const startSession = (sessionId: string | null) => {
    currentSessionId.value = sessionId
  }

  // Clean up session state
  const resetSession = () => {
    currentSessionId.value = null
    isSessionCancelling.value = false
  }

  return {
    // State
    currentSessionId,
    isSessionCancelling,
    
    // Methods
    cancelCurrentSession,
    getSessionStatus,
    getActiveSessions,
    extractSessionId,
    startSession,
    resetSession
  }
}