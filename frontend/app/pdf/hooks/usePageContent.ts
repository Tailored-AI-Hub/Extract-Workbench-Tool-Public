import { useState, useCallback, useRef, useEffect } from 'react';
import { pdfApi, DocumentPageContent, DocumentExtractionJob, AnnotationResponse } from '../../services/pdfApi';

export function usePageContent(
  projectId: string,
  documentId: string,
  token: string | null,
  extractionJobs: DocumentExtractionJob[]
) {
  const [pageContent, setPageContent] = useState<DocumentPageContent[]>([]);
  const [loadingPageContent, setLoadingPageContent] = useState(false);
  const [pageContentError, setPageContentError] = useState<string | null>(null);
  const [annotations, setAnnotations] = useState<AnnotationResponse[]>([]);

  // Refs to store current values without creating dependencies
  const extractionJobsRef = useRef<DocumentExtractionJob[]>([]);
  const currentPageRef = useRef<number>(1);

  // Update refs when state changes
  useEffect(() => {
    extractionJobsRef.current = extractionJobs;
  }, [extractionJobs]);

  const fetchPageContent = useCallback(async (extractorName: string, currentPage: number) => {
    if (!projectId || !documentId || !token || !extractorName) {
      return;
    }

    currentPageRef.current = currentPage;
    const selectedJob = extractionJobsRef.current.find(job => job.extractor === extractorName);
    if (!selectedJob) {
      return;
    }

    try {
      setLoadingPageContent(true);
      setPageContentError(null);
      
      const content = await pdfApi.getExtractionJobPages(
        projectId,
        documentId,
        selectedJob.uuid,
        token
      );
      
      setPageContent(content);
      
      // Also load annotations filtered by selected job and current page
      try {
        const ann = await pdfApi.getAnnotations(documentId, token, { 
          extractionJobUuid: selectedJob.uuid, 
          pageNumber: currentPage 
        });
        setAnnotations(ann);
      } catch (e) {
        console.warn('Failed to load filtered annotations', e);
      }
    } catch (err) {
      console.error('Error fetching page content:', err);
      setPageContentError(err instanceof Error ? err.message : 'Failed to fetch page content');
    } finally {
      setLoadingPageContent(false);
    }
  }, [projectId, documentId, token]);

  return {
    pageContent,
    loadingPageContent,
    pageContentError,
    annotations,
    setAnnotations,
    fetchPageContent
  };
}

