/**
 * Composable for handling message editing and deletion actions
 */

import { ref } from 'vue'
import { useChat, type ChatMessage } from './useChat'

export function useMessageActions() {
  // Message editing state
  const editingMessageId = ref<string | null>(null)
  const editingContent = ref<string>('')
  const editingThinking = ref<string>('')
  
  // Chat composable for update/delete operations
  const { updateMessage, removeMessage } = useChat()
  
  // Start editing a message
  const startEditMessage = (messageId: string, messages: ChatMessage[]) => {
    const msg = messages.find(m => m.id === messageId)
    if (msg) {
      editingMessageId.value = messageId
      editingContent.value = msg.content
      editingThinking.value = msg.thinking || ''
    }
  }
  
  // Cancel editing
  const cancelEditMessage = () => {
    editingMessageId.value = null
    editingContent.value = ''
    editingThinking.value = ''
  }
  
  // Save edited message
  const saveEditMessage = async () => {
    if (!editingMessageId.value) return
    
    try {
      await updateMessage(editingMessageId.value, {
        content: editingContent.value.trim(),
        thinking: editingThinking.value.trim() || undefined
      })
      cancelEditMessage()
    } catch (error) {
      console.error('Failed to update message:', error)
      throw new Error('Failed to update message. Please try again.')
    }
  }
  
  // Delete a message
  const deleteMessage = async (messageId: string) => {
    try {
      await removeMessage(messageId)
    } catch (error) {
      console.error('Failed to delete message:', error)
      throw new Error('Failed to delete message. Please try again.')
    }
  }
  
  // Check if message can be edited (not system messages)
  const canEditMessage = (msg: ChatMessage): boolean => {
    return msg.role !== 'system'
  }
  
  return {
    // State
    editingMessageId,
    editingContent,
    editingThinking,
    
    // Methods
    startEditMessage,
    cancelEditMessage,
    saveEditMessage,
    deleteMessage,
    canEditMessage,
  }
}