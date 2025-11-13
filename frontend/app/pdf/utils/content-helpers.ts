/**
 * Format content for display, extracting text from various structures
 */
export function formatContentForDisplay(content: Record<string, any>): string {
  if (!content || Object.keys(content).length === 0) {
    return "No content available for this page.";
  }

  let textContent = "";
  
  // Check for common text fields
  if (content.text) {
    textContent = content.text;
  } else if (content.content) {
    textContent = content.content;
  } else if (content.extracted_text) {
    textContent = content.extracted_text;
  } else if (content.raw_text) {
    textContent = content.raw_text;
  } else if (Array.isArray(content)) {
    // If content is an array, join all text elements
    textContent = content
      .map(item => typeof item === 'string' ? item : item.text || item.content || '')
      .filter(text => text.trim())
      .join('\n\n');
  } else {
    // If content is an object, try to extract all text values
    const textValues = Object.values(content)
      .filter(value => typeof value === 'string' && value.trim())
      .join('\n\n');
    textContent = textValues || JSON.stringify(content, null, 2);
  }

  return textContent || "No readable text content found.";
}

export interface ContentInfo {
  parsed: any;
  hasCombined: boolean;
  hasText: boolean;
  hasTable: boolean;
  hasMarkdown: boolean;
  hasLatex: boolean;
  hasImages: boolean;
  isStructured: boolean;
}

// Parsed image shape used by renderers
export type ParsedImage = {
  url: string;
  width?: number;
  height?: number;
  bounding_box?: { x1: number; y1: number; x2: number; y2: number };
  order?: number;
};

/**
 * Normalize backend image objects to ParsedImage format
 * Backend provides: { image_url, image_width, image_height, bbox: { Left, Top, Width, Height }, order }
 */
export function parseImagesArray(raw: any): ParsedImage[] {
  if (!raw || !Array.isArray(raw)) return [];

  return (raw as any[])
    .map((item) => {
      if (!item) return null;

      const url = item.image_url ?? null;
      if (!url) return null;

      const width = item.image_width ?? undefined;
      const height = item.image_height ?? undefined;
      const order = item.order ?? undefined;
      const bb = item.bbox ?? null;

      let bounding_box: { x1: number; y1: number; x2: number; y2: number } | undefined;

      // Convert bbox from { Left, Top, Width, Height } to { x1, y1, x2, y2 }
      if (
        bb &&
        typeof bb.Left === 'number' &&
        typeof bb.Top === 'number' &&
        typeof bb.Width === 'number' &&
        typeof bb.Height === 'number'
      ) {
        const L = Number(bb.Left);
        const T = Number(bb.Top);
        const W = Number(bb.Width);
        const H = Number(bb.Height);
        bounding_box = { x1: L, y1: T, x2: L + W, y2: T + H };
      }

      const out: ParsedImage = { url, width, height };
      if (order !== undefined) out.order = order;
      if (bounding_box) out.bounding_box = bounding_box;
      return out;
    })
    .filter(Boolean) as ParsedImage[];
}

/**
 * Determine available content sections and structure
 */
export function getContentInfo(content: any): ContentInfo {
  try {
    const parsed = typeof content === 'string' ? JSON.parse(content) : content;
    if (parsed && typeof parsed === 'object') {
      const combined = parsed.COMBINED && String(parsed.COMBINED).trim() !== '';
      const text = parsed.TEXT && String(parsed.TEXT).trim() !== '';
      const tableValue = parsed.TABLE ?? parsed.TABLES;
      const table = tableValue && String(tableValue).trim() !== '';
      const markdown = parsed.MARKDOWN && String(parsed.MARKDOWN).trim() !== '';
      const latex = parsed.LATEX && String(parsed.LATEX).trim() !== '';
      // IMAGES can be an array, JSON string array, or a formatted text block
      const imagesRaw = parsed.IMAGES;
      const hasImages = parseImagesArray(imagesRaw).length > 0;
      return { 
        parsed, 
        hasCombined: combined, 
        hasText: text, 
        hasTable: table, 
        hasMarkdown: markdown,
        hasLatex: latex,
        hasImages,
        isStructured: true 
      };
    }
  } catch {
    // fallthrough to plain text
  }
  return { 
    parsed: content, 
    hasCombined: false, 
    hasText: true, 
    hasTable: false, 
    hasMarkdown: false,
    hasLatex: false,
    hasImages: false,
    isStructured: false 
  };
}

/**
 * Get content for a specific view mode
 */
export function getContentForViewMode(
  content: any,
  viewMode: 'combined' | 'text' | 'table' | 'markdown' | 'latex' | 'images'
): string {
  const info = getContentInfo(content);
  
  if (!info.isStructured) {
    return formatContentForDisplay(info.parsed);
  }

  const tableValue = info.parsed.TABLE ?? info.parsed.TABLES;
  const contentMap: Record<typeof viewMode, string | undefined> = {
    combined: info.parsed.COMBINED,
    text: info.parsed.TEXT,
    table: tableValue,
    markdown: info.parsed.MARKDOWN,
    latex: info.parsed.LATEX,
    images: ''
  };

  const value = contentMap[viewMode] ?? '';
  return value && String(value).trim() !== '' 
    ? String(value) 
    : 'No content available for this view.';
}

