// Shared TypeScript interfaces

export interface Persona {
  id: string
  name: string
  description: string | null
  template: string
  mode: 'autonomous' | 'reactive'
  loop_frequency: string | null
  first_message: string | null
  image_path: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Module {
  id: string
  name: string
  description: string | null
  content: string
  type: 'simple' | 'advanced'
  trigger_pattern: string | null
  script: string | null
  timing: 'before' | 'after' | 'custom' | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ModuleCreateRequest {
  name: string
  description?: string
  content: string
  type: 'simple' | 'advanced'
  trigger_pattern?: string
  script?: string
  timing?: 'before' | 'after' | 'custom'
}

export interface ModuleUpdateRequest {
  name?: string
  description?: string
  content?: string
  type?: 'simple' | 'advanced'
  trigger_pattern?: string
  script?: string
  timing?: 'before' | 'after' | 'custom'
}

export interface PersonaCreateRequest {
  name: string
  description?: string
  template: string
  mode: 'autonomous' | 'reactive'
  loop_frequency?: string
  first_message?: string
  image_path?: string
}

export interface PersonaUpdateRequest {
  name?: string
  description?: string
  template?: string
  mode?: 'autonomous' | 'reactive'
  loop_frequency?: string
  first_message?: string
  image_path?: string
}