/**
 * Dynamic imports for code splitting heavy components
 * These components are loaded on-demand to reduce initial bundle size
 */

import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';

// Loading component
const LoadingSpinner = () => (
  <div className="flex items-center justify-center p-8">
    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
  </div>
);

// Dynamically import heavy components
export const DynamicLatexRenderer = dynamic(
  () => import('./LatexRenderer').then(mod => ({ default: mod.LatexRenderer })),
  {
    loading: () => <LoadingSpinner />,
    ssr: false, // LaTeX rendering should be client-side only
  }
);

export const DynamicMarkdownRenderer = dynamic(
  () => import('./MarkdownRenderer').then(mod => ({ default: mod.MarkdownRenderer })),
  {
    loading: () => <LoadingSpinner />,
  }
);

export const DynamicImagesRenderer = dynamic(
  () => import('./ImagesRenderer').then(mod => ({ default: mod.ImagesRenderer })),
  {
    loading: () => <LoadingSpinner />,
  }
);

export const DynamicPDFViewer = dynamic(
  () => import('./PDFViewer').then(mod => ({ default: mod.PDFViewer })),
  {
    loading: () => <LoadingSpinner />,
    ssr: false, // PDF rendering must be client-side
  }
);

export const DynamicImageViewer = dynamic(
  () => import('./ImageViewer').then(mod => ({ default: mod.ImageViewer })),
  {
    loading: () => <LoadingSpinner />,
  }
);
