/**
 * Content display component
 * Handles rendering different content types (markdown, latex, images, raw)
 */

import React from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import { LatexRenderer } from './LatexRenderer';
import { ImagesRenderer } from './ImagesRenderer';
import { ContentViewMode } from '../../types';

interface ContentDisplayProps {
  content: Record<string, any> | null;
  contentViewMode: ContentViewMode;
  loading?: boolean;
  error?: string | null;
}

export function ContentDisplay({
  content,
  contentViewMode,
  loading = false,
  error = null,
}: ContentDisplayProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-muted-foreground">Loading content...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-red-600">{error}</div>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-muted-foreground">No content available</div>
      </div>
    );
  }

  // Render based on view mode
  switch (contentViewMode) {
    case 'markdown':
      return <MarkdownRenderer content={content.markdown || ''} />;

    case 'latex':
      return <LatexRenderer content={content.latex || ''} />;

    case 'images':
      return <ImagesRenderer images={content.images || []} />;

    case 'combined':
    default:
      return (
        <div className="space-y-6">
          {content.markdown && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Markdown</h3>
              <MarkdownRenderer content={content.markdown} />
            </div>
          )}
          {content.latex && (
            <div>
              <h3 className="text-lg font-semibold mb-3">LaTeX</h3>
              <LatexRenderer content={content.latex} />
            </div>
          )}
          {content.images && content.images.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Images</h3>
              <ImagesRenderer images={content.images} />
            </div>
          )}
          {!content.markdown && !content.latex && !content.images?.length && (
            <div className="text-sm text-muted-foreground">
              No content available for this page
            </div>
          )}
        </div>
      );
  }
}
