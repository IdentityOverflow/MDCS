/**
 * Composable for managing conversation persistence (database operations)
 */

import { ref, type Ref } from 'vue'
import { useApiConfig } from './apiConfig'
import { usePersonas } from './usePersonas'
import type { ChatMessage, Conversation } from '@/types/chat'

// Shared state for conversation persistence
const currentConversation: Ref<Conversation | null> = ref(null)
const isLoadingConversation = ref(false)
const isSavingMessage = ref(false)

export function useConversationPersistence(
  messages: Ref<ChatMessage[]>,
  error: Ref<string | null>
) {
  const { apiRequest } = useApiConfig()
  const { getPersonaById } = usePersonas()

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

    isSavingMessage.value = true
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
          extra_data: message.extra_data || {}
        })
      })

      if (response.ok) {
        const savedMessage: ChatMessage = await response.json()
        // Update the message with the saved data (including ID from database)
        return {
          ...message,
          id: savedMessage.id,
          conversation_id: savedMessage.conversation_id,
          created_at: savedMessage.created_at,
          updated_at: savedMessage.updated_at
        }
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to save message')
      }
    } finally {
      isSavingMessage.value = false
    }
  }

  // Update message in database
  const updateMessageInDb = async (messageId: string, updates: Partial<ChatMessage>): Promise<void> => {
    try {
      const response = await apiRequest(`/api/messages/${messageId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          content: updates.content,
          thinking: updates.thinking || null,
          input_tokens: updates.input_tokens || null,
          output_tokens: updates.output_tokens || null,
          extra_data: updates.extra_data || {}
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

      if (!response.ok && response.status !== 404) {
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
      // Delete the entire conversation (which cascades to delete messages)
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
        console.error('Failed to clear conversation:', errorData.detail)
        // Don't throw error - conversation clearing should be resilient
      }
    } catch (err) {
      console.error('Clear conversation error:', err)
      // Don't throw error - conversation clearing should be resilient
    }
  }

  return {
    // State
    currentConversation,
    isLoadingConversation,
    isSavingMessage,
    
    // Methods
    loadConversationForPersona,
    createConversationForPersona,
    saveMessageToDb,
    updateMessageInDb,
    deleteMessageFromDb,
    clearConversationInDb
  }
}