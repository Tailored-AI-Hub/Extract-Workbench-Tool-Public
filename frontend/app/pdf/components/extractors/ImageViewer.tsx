'use client'

import React from 'react';
import { useSecureImage } from '../../hooks/useSecureImage';
import { Loader2 } from 'lucide-react';

interface ImageViewerProps {
  imageUrl: string;
  imageError: string | null;
  loading?: boolean;
}

export function ImageViewer({ imageUrl, imageError, loading }: ImageViewerProps) {
  const { src, loading: imgLoading, error } = useSecureImage(imageUrl, {
    tryDirectFirst: false,
    enableCache: true,
  });

  if (loading || imgLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading image...</span>
        </div>
      </div>
    );
  }

  if (imageError || error) {
    return (
      <div className="text-xs text-red-600 px-3 py-2">
        {imageError || error}
      </div>
    );
  }

  if (!src) {
    return null;
  }

  return (
    <div className="w-full flex justify-center">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img 
        src={src}
        alt="Document"
        className="w-full h-auto"
        style={{ 
          display: 'block'
        }}
        onError={(e) => {
          console.error('Failed to load image');
        }}
      />
    </div>
  );
}

