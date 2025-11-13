'use client'

import React from 'react';
import { ContentViewMode } from '../../types';

interface ContentViewSelectorProps {
  viewMode: ContentViewMode;
  onViewModeChange: (mode: ContentViewMode) => void;
  hasCombined: boolean;
  hasText: boolean;
  hasTable: boolean;
  hasMarkdown: boolean;
  hasLatex: boolean;
  hasImages: boolean;
}

export function ContentViewSelector({ 
  viewMode, 
  onViewModeChange, 
  hasCombined, 
  hasText, 
  hasTable,
  hasMarkdown,
  hasLatex,
  hasImages
}: ContentViewSelectorProps) {
  return (
    <div className="flex items-center">
      <div className="flex bg-gray-100 rounded-md p-0.5 h-8">
        {hasCombined && (
          <button
            onClick={() => onViewModeChange('combined')}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all h-7 ${
              viewMode === 'combined' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Combined
          </button>
        )}
        {hasText && (
          <button
            onClick={() => onViewModeChange('text')}
            className={`${hasCombined ? 'ml-0.5' : ''} px-3 py-1.5 text-sm font-medium rounded-md transition-all h-7 ${
              viewMode === 'text' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Text
          </button>
        )}
        {hasTable && (
          <button
            onClick={() => onViewModeChange('table')}
            className={`${hasCombined || hasText ? 'ml-0.5' : ''} px-3 py-1.5 text-sm font-medium rounded-md transition-all h-7 ${
              viewMode === 'table' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Table
          </button>
        )}
        {hasMarkdown && (
          <button
            onClick={() => onViewModeChange('markdown')}
            className={`${hasCombined || hasText || hasTable ? 'ml-0.5' : ''} px-3 py-1.5 text-sm font-medium rounded-md transition-all h-7 ${
              viewMode === 'markdown' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Markdown
          </button>
        )}
        {hasLatex && (
          <button
            onClick={() => onViewModeChange('latex')}
            className={`${hasCombined || hasText || hasTable || hasMarkdown ? 'ml-0.5' : ''} px-3 py-1.5 text-sm font-medium rounded-md transition-all h-7 ${
              viewMode === 'latex' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            LaTeX
          </button>
        )}
        {hasImages && (
          <button
            onClick={() => onViewModeChange('images')}
            className={`${hasCombined || hasText || hasTable || hasMarkdown || hasLatex ? 'ml-0.5' : ''} px-3 py-1.5 text-sm font-medium rounded-md transition-all h-7 ${
              viewMode === 'images' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Images
          </button>
        )}
      </div>
    </div>
  );
}

