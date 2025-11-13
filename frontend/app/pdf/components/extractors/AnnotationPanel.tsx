'use client'

import React from 'react';
import { Loader2, AlertCircle } from "lucide-react";
import AnnotatableText from "../../../components/AnnotatableText";
import { MarkdownRenderer } from './MarkdownRenderer';
import { LatexRenderer } from './LatexRenderer';
import { ImagesRenderer } from './ImagesRenderer';
import { pdfApi, DocumentExtractionJob, AnnotationResponse } from "../../../services/pdfApi";
import { getContentInfo, getContentForViewMode, parseImagesArray } from '../../utils';
import { ContentViewMode } from '../../types';

interface AnnotationPanelProps {
  content: any;
  viewMode: ContentViewMode;
  loading: boolean;
  error: string | null;
  annotations: AnnotationResponse[];
  selectedExtractor: string;
  extractionJobs: DocumentExtractionJob[];
  currentPage: number;
  documentUuid: string;
  token: string | null;
  onAnnotationsChange: (annotations: AnnotationResponse[]) => void;
  highlightedAnnotationId?: string | null;
}

export function AnnotationPanel({
  content,
  viewMode,
  loading,
  error,
  annotations,
  selectedExtractor,
  extractionJobs,
  currentPage,
  documentUuid,
  token,
  onAnnotationsChange,
  highlightedAnnotationId
}: AnnotationPanelProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading page content...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-red-600">
        <AlertCircle className="h-4 w-4" />
        <span>{error}</span>
      </div>
    );
  }

  const currentText = getContentForViewMode(content, viewMode);
  const currentJob = extractionJobs.find(job => job.extractor === selectedExtractor);
  
  // Images mode: render gallery with captions
  if (viewMode === 'images') {
    const info = getContentInfo(content);
    const images = parseImagesArray(info.parsed?.IMAGES);
    return <ImagesRenderer images={images} />;
  }
  
  // For markdown mode, render without annotations
  if (viewMode === 'markdown') {
    return <MarkdownRenderer content={currentText} />;
  }
  
  // Filter and map annotations for latex and other modes
  const initialAnnotations = annotations
    .filter(a => (
      (a.page_number == null || a.page_number === currentPage) &&
      (a.extraction_job_uuid == null || (currentJob && a.extraction_job_uuid === currentJob.uuid))
    ))
    .map(a => {
      const fragment = (a.text || '').slice(a.selection_start ?? 0, a.selection_end ?? 0);
      const idx = fragment ? currentText.indexOf(fragment) : -1;
      const start = idx >= 0 ? idx : (a.selection_start ?? 0);
      const end = idx >= 0 ? idx + fragment.length : (a.selection_end ?? 0);
      return { id: a.uuid, start, end, comment: a.comment || '' };
    });
  
  // For latex mode, render with annotations
  if (viewMode === 'latex') {
    return (
      <LatexRenderer 
        content={currentText} 
        initialAnnotations={initialAnnotations}
        onCreate={async ({ start, end, comment }) => {
          if (!documentUuid || !token) return;
          const selectedJob = extractionJobs.find(job => job.extractor === selectedExtractor);
          if (!selectedJob) return;
          
          const created = await pdfApi.createAnnotation({
            documentId: documentUuid,
            extractionJobUuid: selectedJob.uuid,
            pageNumber: currentPage,
            text: currentText,
            comment,
            selectionStart: start,
            selectionEnd: end,
          }, token);
          
          onAnnotationsChange([...annotations, created]);
          return { id: created.uuid };
        }}
        onDelete={async (id) => {
          if (!token) return;
          try {
            await pdfApi.deleteAnnotation(id, token);
            onAnnotationsChange(annotations.filter(a => a.uuid !== id));
          } catch {}
        }}
        highlightedAnnotationId={highlightedAnnotationId}
      />
    );
  }

  return (
    <AnnotatableText
      text={currentText}
      initialAnnotations={initialAnnotations}
      onCreate={async ({ start, end, comment }) => {
        if (!documentUuid || !token) return;
        const selectedJob = extractionJobs.find(job => job.extractor === selectedExtractor);
        if (!selectedJob) return;
        
        const created = await pdfApi.createAnnotation({
          documentId: documentUuid,
          extractionJobUuid: selectedJob.uuid,
          pageNumber: currentPage,
          text: currentText,
          comment,
          selectionStart: start,
          selectionEnd: end,
        }, token);
        
        onAnnotationsChange([...annotations, created]);
        return { id: created.uuid };
      }}
      onDelete={async (id) => {
        if (!token) return;
        try {
          await pdfApi.deleteAnnotation(id, token);
          onAnnotationsChange(annotations.filter(a => a.uuid !== id));
        } catch {}
      }}
      highlightedAnnotationId={highlightedAnnotationId}
    />
  );
}

