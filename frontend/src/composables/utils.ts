// Shared utility functions
import personaDefaultImage from '@/assets/persona.png'

/**
 * Truncates a description to a specified length
 */
export function truncateDescription(description: string, maxLength: number = 100): string {
  if (description.length <= maxLength) {
    return description
  }
  return description.substring(0, maxLength).trim() + '...'
}

/**
 * Gets persona image URL with fallback
 */
export function getPersonaImage(imagePath: string | null | undefined): string {
  if (imagePath && imagePath.startsWith('/static/')) {
    return `http://localhost:8000${imagePath}`
  }
  return imagePath || personaDefaultImage
}

/**
 * Handles image loading errors with fallback
 * Prevents infinite loop by marking the image as having failed once
 */
export function handleImageError(event: Event): void {
  const img = event.target as HTMLImageElement

  // Prevent infinite loop - only try fallback once
  if (img.dataset.fallbackAttempted === 'true') {
    return
  }

  img.dataset.fallbackAttempted = 'true'
  img.src = personaDefaultImage
}

/**
 * Counts template components in a template string
 */
export function countComponents(template: string): number {
  const matches = template.match(/@([a-z][a-z0-9_]{0,49})/g)
  return matches ? matches.length : 0
}