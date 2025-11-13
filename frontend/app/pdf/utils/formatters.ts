/**
 * Format a date string into a human-readable relative time
 */
export function formatDate(dateString: string): string {
  const parsed = parseFlexibleDate(dateString);
  if (!parsed) return dateString;

  const now = new Date();
  let diffInMinutes = Math.floor((now.getTime() - parsed.getTime()) / (1000 * 60));

  if (diffInMinutes < 0) diffInMinutes = 0;

  if (diffInMinutes < 1) return 'Just now';
  if (diffInMinutes < 60) {
    const m = diffInMinutes;
    return `${m} minute${m === 1 ? '' : 's'} ago`;
  }

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    const h = diffInHours;
    return `${h} hour${h === 1 ? '' : 's'} ago`;
  }

  const diffInDays = Math.floor(diffInHours / 24);
  const d = diffInDays;
  return `${d} day${d === 1 ? '' : 's'} ago`;
}

function parseFlexibleDate(input: string): Date | null {
  if (!input) return null;
  const normalized = input.replace(/\u200E|\u200F/g, '').trim();

  // Try native (ISO etc.)
  const native = new Date(normalized);
  if (!isNaN(native.getTime())) return native;

  // Try DD/MM/YYYY or DD-MM-YYYY with optional time HH:MM[:SS]
  const datePart = normalized.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
  if (datePart) {
    const day = Number(datePart[1]);
    const month = Number(datePart[2]) - 1;
    const year = Number(datePart[3]);

    const timePart = normalized.match(/(\d{1,2}):(\d{2})(?::(\d{2}))?/);
    const hours = timePart ? Number(timePart[1]) : 0;
    const minutes = timePart ? Number(timePart[2]) : 0;
    const seconds = timePart && timePart[3] ? Number(timePart[3]) : 0;

    const d = new Date(year, month, day, hours, minutes, seconds);
    if (!isNaN(d.getTime())) return d;
  }

  return null;
}

/**
 * Format latency in milliseconds to seconds with 2 decimal places
 */
export function formatLatency(latencyMs: number | null | undefined): string {
  if (!latencyMs) return "-";
  return `${(latencyMs / 1000).toFixed(2)}s`;
}

/**
 * Format cost to 4 decimal places with dollar sign
 */
export function formatCost(cost: number | null | undefined): string {
  return `$${(cost || 0).toFixed(4)}`;
}

/**
 * Format rating display
 */
export function formatRating(rating: number | null | undefined): string | null {
  if (!rating) return null;
  return `${rating}/5`;
}

/**
 * Format document extractor name (fallback only - prefer using extractor_display_name from API)
 * This is kept for backwards compatibility when display_name might not be available.
 */
export function formatDocumentExtractorName(name: string): string {
  if (!name) return ''
  
  // Basic capitalization fallback - backend should provide extractor_display_name
  return name
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

