/**
 * Composable for managing chat session lifecycle and cancellation
 */

import { ref, type Ref } from 'vue'
import { useApiConfig } from './apiConfig'

// Shared session state
const currentSessionId = ref<string | null>(null)
const isSessionCancelling = ref(false)

// Debug logging disabled for production

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
    console.log('🛑 DEBUG: Cancel request - currentSessionId:', currentSessionId.value)
    console.log('🛑 DEBUG: Cancel request - isSessionCancelling:', isSessionCancelling.value)
    
    if (!currentSessionId.value || isSessionCancelling.value) {
      console.log('🛑 DEBUG: Cancel request blocked - no session ID or already cancelling')
      return false
    }

    // Store the session ID we're trying to cancel (in case it changes during request)
    const sessionToCancel = currentSessionId.value
    isSessionCancelling.value = true
    console.log('🛑 DEBUG: Attempting to cancel session:', sessionToCancel)
    
    try {
      // Use the new cancellation endpoints
      const response = await apiRequest(`/api/chat/cancel/${sessionToCancel}`, {
        method: 'POST'
      })

      if (response.ok) {
        const result = await response.json()
        console.log('🛑 DEBUG: Session cancellation result:', result)
        console.log('🛑 DEBUG: Cancelled session:', sessionToCancel)
        
        // Clean up session state only if cancellation was successful
        if (result.cancelled) {
          console.log('🛑 DEBUG: Cancellation successful - cleaning up state')
          currentSessionId.value = null
          isStreaming.value = false
          processingStage.value = null
          stageMessage.value = null
          currentStreamingMessage.value = ''
          currentStreamingThinking.value = ''
        } else {
          console.log('🛑 DEBUG: Cancellation failed - keeping current state')
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
    console.log('🚀 DEBUG: Starting session with ID:', sessionId)
    console.log('🚀 DEBUG: Previous session ID was:', currentSessionId.value)
    console.log('🚀 DEBUG: isSessionCancelling:', isSessionCancelling.value)
    
    // Don't update session ID if we're in the middle of cancelling
    if (isSessionCancelling.value) {
      console.log('🚀 DEBUG: Skipping session update - cancellation in progress')
      return
    }
    
    currentSessionId.value = sessionId
    console.log('🚀 DEBUG: Session ID set to:', currentSessionId.value)
  }

  // Clean up session state
  const resetSession = () => {
    console.log('🔄 DEBUG: Resetting session - previous ID was:', currentSessionId.value)
    currentSessionId.value = null
    isSessionCancelling.value = false
    console.log('🔄 DEBUG: Session reset complete')
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