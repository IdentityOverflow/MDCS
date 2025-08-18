// Shared utility functions

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
 * Gets persona image path with fallback
 */
export function getPersonaImage(imagePath: string): string {
  return imagePath || '/src/assets/persona.png'
}

/**
 * Handles image loading errors with fallback
 */
export function handleImageError(event: Event): void {
  const img = event.target as HTMLImageElement
  if (img.src !== '/src/assets/persona.png') {
    img.src = '/src/assets/persona.png'
  }
}

/**
 * Counts template components in a template string
 */
export function countComponents(template: string): number {
  const matches = template.match(/\{[^}]*_module\}/g) || template.match(/\{[^}]*module[^}]*\}/g)
  return matches ? matches.length : 0
}