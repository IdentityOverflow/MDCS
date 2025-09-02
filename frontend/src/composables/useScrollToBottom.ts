/**
 * Composable for auto-scroll functionality
 */

import { nextTick, watch, type Ref } from 'vue'

export function useScrollToBottom(
  messages: Ref<any[]>, 
  isStreaming: Ref<boolean>,
  currentStreamingMessage: Ref<string>,
  currentStreamingThinking: Ref<string>
) {
  
  // Scroll to bottom function - takes container ref as parameter
  const scrollToBottom = (container?: HTMLElement) => {
    nextTick(() => {
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    })
  }
  
  // Create a scrollToBottom function that can be called with different containers
  const createScrollHandler = (containerRef: Ref<HTMLElement | undefined>) => {
    return () => scrollToBottom(containerRef.value)
  }
  
  // Auto-scroll watchers - they need to be set up with a container reference
  const setupAutoScroll = (containerRef: Ref<HTMLElement | undefined>) => {
    const scrollHandler = createScrollHandler(containerRef)
    
    watch(messages, scrollHandler, { deep: true })

    watch([currentStreamingMessage, currentStreamingThinking], () => {
      if (isStreaming.value) {
        scrollHandler()
      }
    })
  }
  
  return {
    scrollToBottom,
    createScrollHandler,
    setupAutoScroll
  }
}