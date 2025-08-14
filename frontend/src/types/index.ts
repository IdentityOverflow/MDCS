// Shared TypeScript interfaces

export interface Persona {
  id: string
  name: string
  description: string
  model: string
  template: string
  mode: 'autonomous' | 'reactive'
  loop_frequency?: number
  first_message?: string
  image: string
}

export interface Module {
  id: string
  name: string
  description: string
  content: string
  type: 'simple' | 'advanced'
  trigger_pattern?: string
  script?: string
  timing?: 'before' | 'after' | 'custom'
}