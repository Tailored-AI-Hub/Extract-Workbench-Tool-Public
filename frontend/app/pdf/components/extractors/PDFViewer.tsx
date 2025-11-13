'use client'

import React from 'react';
import { Loader2 } from 'lucide-react';

interface PDFViewerProps {
  canvasRef: React.RefObject<HTMLCanvasElement>;
  pdfError: string | null;
  loading?: boolean;
}

export function PDFViewer({ canvasRef, pdfError, loading }: PDFViewerProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading PDF...</span>
        </div>
      </div>
    );
  }

  if (pdfError) {
    return (
      <div className="text-xs text-red-600 px-3 py-2">
        {pdfError}
      </div>
    );
  }

  return (
    <canvas 
      ref={canvasRef} 
      className="max-w-full h-auto shadow-sm border border-gray-200 rounded" 
    />
  );
}

