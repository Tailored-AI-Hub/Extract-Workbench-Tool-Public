/**
 * Format extractor name (fallback only - prefer using extractor_display_name from API)
 * This is kept for backwards compatibility when display_name might not be available.
 */
export function formatAudioExtractorName(name?: string | null): string {
  if (!name) return ''
  
  // Basic capitalization fallback - backend should provide extractor_display_name
  return name
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}


