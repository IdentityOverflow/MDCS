/**
 * Composable for managing thinking content visibility
 */

import { ref } from 'vue'

export function useThinkingToggle() {
  const expandedThinking = ref<Set<string>>(new Set())
  
  // Toggle thinking content visibility
  const toggleThinking = (messageId: string) => {
    if (expandedThinking.value.has(messageId)) {
      expandedThinking.value.delete(messageId)
    } else {
      expandedThinking.value.add(messageId)
    }
  }
  
  // Check if thinking is expanded for a message
  const isThinkingExpanded = (messageId: string): boolean => {
    return expandedThinking.value.has(messageId)
  }
  
  // Expand thinking (useful for edit mode)
  const expandThinking = (messageId: string) => {
    expandedThinking.value.add(messageId)
  }
  
  // Collapse thinking
  const collapseThinking = (messageId: string) => {
    expandedThinking.value.delete(messageId)
  }
  
  // Clear all expanded thinking
  const clearExpandedThinking = () => {
    expandedThinking.value.clear()
  }
  
  return {
    // State
    expandedThinking,
    
    // Methods
    toggleThinking,
    isThinkingExpanded,
    expandThinking,
    collapseThinking,
    clearExpandedThinking
  }
}