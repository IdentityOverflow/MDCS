/**
 * Composable for managing personas state and API operations
 */

import { ref, computed, type Ref } from 'vue'
import type { Persona, PersonaCreateRequest, PersonaUpdateRequest } from '@/types'
import { useApiConfig } from './apiConfig'

// Global state for personas
const personas: Ref<Persona[]> = ref([])
const loading = ref(false)
const error = ref<string | null>(null)

export function usePersonas() {
  const apiConfig = useApiConfig()

  // Computed values
  const reactivePersonas = computed(() => 
    personas.value.filter(p => p.mode === 'reactive' && p.is_active)
  )
  
  const autonomousPersonas = computed(() => 
    personas.value.filter(p => p.mode === 'autonomous' && p.is_active)
  )

  const getPersonaById = (id: string) => 
    personas.value.find(p => p.id === id)

  // API operations
  const fetchPersonas = async (filters?: { mode?: string; active_only?: boolean }) => {
    loading.value = true
    error.value = null
    
    try {
      const params = new URLSearchParams()
      
      if (filters?.mode) {
        params.append('mode', filters.mode)
      }
      
      if (filters?.active_only !== undefined) {
        params.append('active_only', filters.active_only.toString())
      } else {
        params.append('active_only', 'true') // Default to active only
      }
      
      const endpoint = params.toString() ? `/api/personas?${params}` : `/api/personas`
      
      const response = await apiConfig.apiRequest(endpoint, {
        method: 'GET',
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch personas: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      personas.value = data
      
      console.log(`Fetched ${data.length} personas`)
      return data
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error fetching personas'
      error.value = message
      console.error('Error fetching personas:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchPersonaById = async (id: string): Promise<Persona> => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiConfig.apiRequest(`/api/personas/${id}`, {
        method: 'GET',
      })

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`Persona with ID ${id} not found`)
        }
        throw new Error(`Failed to fetch persona: ${response.status} ${response.statusText}`)
      }

      const persona = await response.json()
      
      // Update local state if persona exists in array
      const index = personas.value.findIndex(p => p.id === id)
      if (index !== -1) {
        personas.value[index] = persona
      }
      
      return persona
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error fetching persona'
      error.value = message
      console.error('Error fetching persona:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const createPersona = async (personaData: PersonaCreateRequest): Promise<Persona> => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiConfig.apiRequest(`/api/personas`, {
        method: 'POST',
        body: JSON.stringify(personaData),
      })

      if (!response.ok) {
        if (response.status === 422) {
          const errorData = await response.json()
          throw new Error(`Validation error: ${JSON.stringify(errorData.detail)}`)
        }
        throw new Error(`Failed to create persona: ${response.status} ${response.statusText}`)
      }

      const newPersona = await response.json()
      
      // Add to local state
      personas.value.unshift(newPersona) // Add to beginning for newest first
      
      console.log('Created persona:', newPersona.id)
      return newPersona
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error creating persona'
      error.value = message
      console.error('Error creating persona:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const updatePersona = async (id: string, updateData: PersonaUpdateRequest): Promise<Persona> => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiConfig.apiRequest(`/api/personas/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updateData),
      })

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`Persona with ID ${id} not found`)
        }
        if (response.status === 422) {
          const errorData = await response.json()
          throw new Error(`Validation error: ${JSON.stringify(errorData.detail)}`)
        }
        throw new Error(`Failed to update persona: ${response.status} ${response.statusText}`)
      }

      const updatedPersona = await response.json()
      
      // Update local state
      const index = personas.value.findIndex(p => p.id === id)
      if (index !== -1) {
        personas.value[index] = updatedPersona
      }
      
      console.log('Updated persona:', id)
      return updatedPersona
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error updating persona'
      error.value = message
      console.error('Error updating persona:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const deletePersona = async (id: string): Promise<void> => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiConfig.apiRequest(`/api/personas/${id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`Persona with ID ${id} not found`)
        }
        throw new Error(`Failed to delete persona: ${response.status} ${response.statusText}`)
      }

      // Remove from local state
      const index = personas.value.findIndex(p => p.id === id)
      if (index !== -1) {
        personas.value.splice(index, 1)
      }
      
      console.log('Deleted persona:', id)
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error deleting persona'
      error.value = message
      console.error('Error deleting persona:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const uploadPersonaImage = async (file: File): Promise<string> => {
    loading.value = true
    error.value = null
    
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await apiConfig.apiRequest(`/api/personas/upload-image`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header, let browser set it for FormData
        headers: {}
      })

      if (!response.ok) {
        if (response.status === 400) {
          const errorData = await response.json()
          throw new Error(`Invalid file: ${errorData.detail}`)
        }
        throw new Error(`Failed to upload image: ${response.status} ${response.statusText}`)
      }

      const result = await response.json()
      console.log('Uploaded persona image:', result.image_path)
      
      return result.image_path
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error uploading image'
      error.value = message
      console.error('Error uploading persona image:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Utility functions
  const clearError = () => {
    error.value = null
  }

  const clearPersonas = () => {
    personas.value = []
  }

  const refreshPersonas = async () => {
    await fetchPersonas()
  }

  return {
    // State
    personas: readonly(personas),
    loading: readonly(loading),
    error: readonly(error),
    
    // Computed
    reactivePersonas,
    autonomousPersonas,
    
    // Methods
    getPersonaById,
    fetchPersonas,
    fetchPersonaById,
    createPersona,
    updatePersona,
    deletePersona,
    uploadPersonaImage,
    clearError,
    clearPersonas,
    refreshPersonas,
  }
}

// Helper function to make state readonly
function readonly<T>(ref: Ref<T>): Readonly<Ref<T>> {
  return ref as Readonly<Ref<T>>
}