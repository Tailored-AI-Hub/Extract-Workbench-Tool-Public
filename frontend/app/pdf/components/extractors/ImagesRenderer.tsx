'use client'

import React from 'react';
import Image from 'next/image';
import { useSecureImage } from '../../hooks/useSecureImage';

type BoundingBox = { x1: number; y1: number; x2: number; y2: number };

type ImageItem = {
  url: string;
  width?: number;
  height?: number;
  bounding_box?: BoundingBox;
  order?: number;
};

interface ImagesRendererProps {
  images: ImageItem[];
}

export function ImagesRenderer({ images }: ImagesRendererProps) {
  const fmt = (n?: number) => (typeof n === 'number' ? n.toFixed(2) : '—');

  if (!images || images.length === 0) {
    return <div className="text-sm text-muted-foreground">No images.</div>;
  }

  return (
    <div className="flex flex-col gap-6">
      {images.map((img, index) => (
        <ImageFigure key={index} img={img} index={index} fmt={fmt} />
      ))}
    </div>
  );
}

function ImageFigure({ img, index, fmt }: { img: ImageItem; index: number; fmt: (n?: number) => string }) {
  const { src, loading, error } = useSecureImage(img.url, {
    tryDirectFirst: false,
    enableCache: true,
  });

  const imageTitle = img.order ? `IMAGE_${img.order}` : `IMAGE_${index + 1}`;

  return (
    <figure className="border rounded-md overflow-hidden bg-white">
      {/* Title centered above the image */}
      <div className="text-center font-semibold text-lg py-3 border-b bg-gray-50">
        {imageTitle}
      </div>
      
      {/* Image content with zoom on click, maintaining aspect ratio */}
      <div className="p-4 flex justify-center items-center bg-gray-50">
        {loading ? (
          <div className="w-full h-32 flex items-center justify-center text-xs text-gray-500">Loading image…</div>
        ) : error ? (
          <div className="w-full h-32 flex items-center justify-center text-xs text-red-600">{error}</div>
        ) : (
          <div className="relative w-full flex justify-center">
            <Image
              src={src ?? ''}
              alt={imageTitle}
              width={img.width ?? 800}
              height={img.height ?? 600}
              className="max-w-full h-auto object-contain cursor-zoom-in hover:opacity-90 transition-opacity"
              style={{ maxHeight: '600px' }}
              onClick={() => {
                // Open image in new tab for full zoom
                window.open(src ?? '', '_blank');
              }}
              unoptimized
              loading="lazy"
            />
          </div>
        )}
      </div>

      {/* Metadata caption */}
      <figcaption className="text-xs text-gray-600 p-3 border-t bg-white">
        <div className="grid grid-cols-2 gap-2">
          <div>Width: {img.width ?? '—'}</div>
          <div>Height: {img.height ?? '—'}</div>
        </div>
        {img.bounding_box && (
          <div className="mt-2 text-gray-500">
            Bounding Box: x1 {fmt(img.bounding_box.x1)}, y1 {fmt(img.bounding_box.y1)}, x2 {fmt(img.bounding_box.x2)}, y2 {fmt(img.bounding_box.y2)}
          </div>
        )}
      </figcaption>
    </figure>
  );
}


