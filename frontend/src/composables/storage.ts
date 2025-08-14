// Browser localStorage management composable

import { ref } from 'vue'
import type { Ref } from 'vue'

export interface StorageConfig<T> {
  key: string
  defaultValue: T
  validate?: (value: any) => boolean
}

/**
 * Composable for managing data in localStorage with Vue reactivity
 */
export function useLocalStorage<T>(config: StorageConfig<T>): {
  data: Ref<T>
  save: () => boolean
  load: () => boolean
  clear: () => void
  isLoaded: Ref<boolean>
} {
  const { key, defaultValue, validate } = config
  const data = ref<T>(structuredClone(defaultValue)) as Ref<T>
  const isLoaded = ref(false)

  /**
   * Save current data to localStorage
   */
  function save(): boolean {
    try {
      const serialized = JSON.stringify(data.value)
      localStorage.setItem(key, serialized)
      return true
    } catch (error) {
      console.error(`Failed to save to localStorage (${key}):`, error)
      return false
    }
  }

  /**
   * Load data from localStorage
   */
  function load(): boolean {
    try {
      const stored = localStorage.getItem(key)
      if (stored === null) {
        // No stored data, use default
        data.value = structuredClone(defaultValue)
        isLoaded.value = true
        return true
      }

      const parsed = JSON.parse(stored)
      
      // Validate if validation function provided
      if (validate && !validate(parsed)) {
        console.warn(`Invalid data in localStorage (${key}), using default`)
        data.value = structuredClone(defaultValue)
        isLoaded.value = true
        return false
      }

      // Merge with default to handle new fields
      data.value = { ...structuredClone(defaultValue), ...parsed }
      isLoaded.value = true
      return true
    } catch (error) {
      console.error(`Failed to load from localStorage (${key}):`, error)
      data.value = structuredClone(defaultValue)
      isLoaded.value = true
      return false
    }
  }

  /**
   * Clear data from localStorage and reset to default
   */
  function clear(): void {
    localStorage.removeItem(key)
    data.value = structuredClone(defaultValue)
  }

  return {
    data,
    save,
    load,
    clear,
    isLoaded
  }
}

/**
 * Utility to show temporary success/error messages
 */
export function useNotification() {
  const message = ref('')
  const type = ref<'success' | 'error' | ''>('')
  const isVisible = ref(false)

  function show(text: string, notificationType: 'success' | 'error', duration = 3000) {
    message.value = text
    type.value = notificationType
    isVisible.value = true
    
    setTimeout(() => {
      isVisible.value = false
      setTimeout(() => {
        message.value = ''
        type.value = ''
      }, 300)
    }, duration)
  }

  function showSuccess(text: string, duration?: number) {
    show(text, 'success', duration)
  }

  function showError(text: string, duration?: number) {
    show(text, 'error', duration)
  }

  return {
    message,
    type,
    isVisible,
    showSuccess,
    showError
  }
}