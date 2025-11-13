'use client'

import Link from "next/link";
import { useParams } from "next/navigation";
import React, { useState, useEffect, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../../../components/ui/card";
import { Button } from "../../../../../../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../../../../components/ui/tabs";
import { ArrowLeft, Loader2, AlertCircle } from "lucide-react";
import Layout from "../../../../../../components/Layout";
import { pdfApi, DocumentExtractionJob, Document as ApiDocument, FeedbackResponse, PageAverageRating, Project } from "../../../../../../services/pdfApi";
import { API_BASE_URL } from "../../../../../../services/api";
import { useAuth } from "../../../../../../contexts/AuthContext";
import { usePDFViewer, usePageContent, useExtractionJobPolling } from "../../../../../hooks";
import { 
  PDFViewer,
  PageNavigation, 
  RatingControl, 
  ExtractorSelector, 
  ContentViewSelector, 
  AnnotationPanel, 
  ExtractionJobsTable,
  AnnotationsListTable
} from "../../../../../components/extractors";
import { getContentInfo, getContentForViewMode, hasSuccessfulExtractor } from "../../../../../utils";
import { ContentViewMode, SortField, SortDirection } from "../../../../../types";


export default function FileExtractorsPage() {
  const params = useParams();
  const projectId = params?.projectId as string;
  const documentId = params?.documentId as string;
  const { token, loading: authLoading, retryAuth } = useAuth();
  
  // UI state
  const [activeTab, setActiveTab] = useState("summary");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedExtractor, setSelectedExtractor] = useState("");
  const [contentViewMode, setContentViewMode] = useState<ContentViewMode>('combined');
  const [ratingFilter, setRatingFilter] = useState<'all' | 'my'>('all');
  
  // State for highlighting a specific annotation
  const [highlightedAnnotationId, setHighlightedAnnotationId] = useState<string | null>(null);
  
  // Ref to track if we're navigating from an annotation click (to prevent auto view mode override)
  const isNavigatingFromAnnotationClick = useRef(false);
  
  // Rating state
  const [rating, setRating] = useState(0);
  const [submittingRating, setSubmittingRating] = useState(false);
  const [ratingError, setRatingError] = useState<string | null>(null);
  const [pageAverageRating, setPageAverageRating] = useState<PageAverageRating | null>(null);
  const [loadingAverageRating, setLoadingAverageRating] = useState(false);
  
  // API data states
  const [project, setProject] = useState<Project | null>(null);
  const [extractionJobs, setExtractionJobs] = useState<DocumentExtractionJob[]>([]);
  const [doc, setDoc] = useState<ApiDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  
  // Feedback state
  const [pageFeedback, setPageFeedback] = useState<FeedbackResponse[]>([]);
  const [loadingPageFeedback, setLoadingPageFeedback] = useState(false);

  const totalPages = doc?.page_count || 0;
  const fileUrl = doc ? `${API_BASE_URL}/projects/${projectId}/documents/${documentId}/pdf-load` : '';

  // PDF viewer hook - document projects only support PDFs
  const pdfViewerResult = usePDFViewer(
    fileUrl, 
    token, 
    activeTab, 
    currentPage, 
    setCurrentPage
  );
  const { pageContent, loadingPageContent, pageContentError, annotations, setAnnotations, fetchPageContent } = usePageContent(projectId, documentId, token, extractionJobs);
  const { retryingJobs, retryExtractionJob, fetchExtractionJobs } = useExtractionJobPolling(projectId, documentId, token, extractionJobs, setExtractionJobs, ratingFilter === 'my');

  // Fetch data on component mount and when rating filter changes
  useEffect(() => {
    const fetchData = async () => {
      if (!projectId || !documentId || !token) {
        return;
      }
      
      try {
        setLoading(true);
        setError(null);

        // Fetch project, document and extraction jobs in parallel
        const [projectData, documentData, jobsData] = await Promise.all([
          pdfApi.getProject(projectId, token),
          pdfApi.getDocument(projectId, documentId, token),
          pdfApi.getDocumentExtractionJobs(projectId, documentId, token, ratingFilter === 'my')
        ]);

        setProject(projectData);
        setDoc(documentData);
        setExtractionJobs(jobsData);
        
        // Set default selected extractor to the first successful one (only on initial load)
        if (!selectedExtractor) {
          const successfulJob = jobsData.find(job => job.status === 'Success');
          if (successfulJob) {
            setSelectedExtractor(successfulJob.extractor);
          }
        }
        
      } catch (err) {
        console.error('Error fetching data:', err);
        if (err instanceof Error) {
          setError(`Failed to fetch data: ${err.message}`);
        } else {
          setError('Failed to fetch data');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [projectId, documentId, token, ratingFilter, selectedExtractor]);

  // Handle rating change
  const handleRatingChange = async (newRating: number) => {
    if (!token || !projectId || !documentId) return;
    const previous = rating;
    setRating(newRating); // optimistic update
    setRatingError(null);
    setSubmittingRating(true);
    try {
      const selectedJob = extractionJobs.find(job => job.extractor === selectedExtractor);
      if (!selectedJob || !doc) return;
      
      // Submit the rating
      await pdfApi.submitFeedback(
        projectId,
        documentId,
        {
          document_uuid: doc.uuid,
          page_number: currentPage,
          extraction_job_uuid: selectedJob.uuid,
          rating: newRating,
          comment: ''
        },
        token
      );
      
      // Immediately fetch updated average rating after successful submission
      try {
        const updatedAverageRating = await pdfApi.getPageAverageRating(
          projectId,
          documentId,
          currentPage,
          selectedJob.uuid,
          token
        );
        setPageAverageRating(updatedAverageRating);
      } catch (error) {
        console.error('Error fetching updated average rating:', error);
      }
      
      // Refresh feedback for the page to reflect latest server state
      try {
        const fb = await pdfApi.getPageFeedback(projectId, documentId, currentPage, token);
        setPageFeedback(fb);
      } catch {}
    } catch (e) {
      setRating(previous);
      setRatingError(e instanceof Error ? e.message : 'Failed to submit rating');
    } finally {
      setSubmittingRating(false);
    }
  };

  // Fetch page average rating
  const fetchPageAverageRating = useCallback(async () => {
    if (!token || !projectId || !documentId || !doc || !selectedExtractor) return;
    
    // Find the selected job to get its UUID
    const selectedJob = extractionJobs.find(job => job.extractor === selectedExtractor);
    if (!selectedJob) return;
    
    try {
      setLoadingAverageRating(true);
      const averageRating = await pdfApi.getPageAverageRating(
        projectId,
        documentId,
        currentPage,
        selectedJob.uuid,
        token
      );
      setPageAverageRating(averageRating);
      // Set the user's existing rating (or 0 if they haven't rated)
      // Safeguard: Only set rating to 0 if user_rating is null/undefined
      if (averageRating.user_rating === null || averageRating.user_rating === undefined) {
        setRating(0);
      } else {
        setRating(averageRating.user_rating);
      }
    } catch (error) {
      console.error('Error fetching average rating:', error);
      // Set to null on error to show "--" in UI
      setPageAverageRating(null);
      setRating(0);
    } finally {
      setLoadingAverageRating(false);
    }
  }, [token, projectId, documentId, doc, selectedExtractor, extractionJobs, currentPage]);

  // Fetch average rating when dependencies change
  useEffect(() => {
    fetchPageAverageRating();
  }, [fetchPageAverageRating]);

  // Auto-load successful extractor when switching to Annotation tab
  // Only set extractor, don't reset page
  useEffect(() => {
    if (activeTab === "annotation" && doc && extractionJobs.length > 0) {
      if (!selectedExtractor) {
        const successfulJob = extractionJobs.find(job => job.status === 'Success');
        if (successfulJob) {
          setSelectedExtractor(successfulJob.extractor);
        }
      } else {
        const currentJob = extractionJobs.find(job => job.extractor === selectedExtractor);
        if (!currentJob || currentJob.status !== 'Success') {
          const successfulJob = extractionJobs.find(job => job.status === 'Success');
          if (successfulJob) {
            setSelectedExtractor(successfulJob.extractor);
          }
        }
      }
    }
  }, [activeTab, doc, extractionJobs, selectedExtractor]);

  // Ensure selected extractor is always successful when extraction jobs change
  useEffect(() => {
    if (selectedExtractor && extractionJobs.length > 0) {
      const currentJob = extractionJobs.find(job => job.extractor === selectedExtractor);
      if (!currentJob || currentJob.status !== 'Success') {
        const successfulJob = extractionJobs.find(job => job.status === 'Success');
        if (successfulJob) {
          setSelectedExtractor(successfulJob.extractor);
        }
      }
    }
  }, [extractionJobs, selectedExtractor]);

  // Fetch page content when selected extractor changes
  useEffect(() => {
    if (selectedExtractor && projectId && documentId && token) {
      fetchPageContent(selectedExtractor, currentPage);
    }
  }, [selectedExtractor, projectId, documentId, token, currentPage, fetchPageContent]);

  // Refresh annotations for new page
  useEffect(() => {
    if (selectedExtractor && projectId && documentId && token) {
      const selectedJob = extractionJobs.find(job => job.extractor === selectedExtractor);
      if (selectedJob) {
        pdfApi.getAnnotations(documentId, token, { extractionJobUuid: selectedJob.uuid, pageNumber: currentPage })
          .then(setAnnotations)
          .catch(() => {});
      }
    }
  }, [currentPage, selectedExtractor, projectId, documentId, token, extractionJobs, setAnnotations]);

  // Get content for current page
  const getCurrentPageContent = () => {
    const currentPageData = pageContent.find(page => page.page_number === currentPage);
    return currentPageData?.content || {};
  };

  // Reset the content view mode based on the newly loaded page/extractor
  // Only reset view mode, don't reset the page
  useEffect(() => {
    // Skip auto-selection if we're navigating from an annotation click
    if (isNavigatingFromAnnotationClick.current) {
      isNavigatingFromAnnotationClick.current = false;
      return;
    }
    
    const info = getContentInfo(getCurrentPageContent());
    
    // Priority: Combined > Markdown > LaTeX > Text > Table > Images
    if (info.hasCombined) {
      setContentViewMode('combined');
    } else if (info.hasMarkdown) {
      setContentViewMode('markdown');
    } else if (info.hasLatex) {
      setContentViewMode('latex');
    } else if (info.hasText) {
      setContentViewMode('text');
    } else if (info.hasTable) {
      setContentViewMode('table');
    } else if (info.hasImages) {
      setContentViewMode('images');
    } else {
      // Fallback to text if no content is available yet
      setContentViewMode('text');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, selectedExtractor, pageContent]);

  // Fetch page feedback when page/extractor changes
  useEffect(() => {
    const run = async () => {
      if (!projectId || !documentId || !token || !currentPage) return;
      setLoadingPageFeedback(true);
      try {
        const fb = await pdfApi.getPageFeedback(projectId, documentId, currentPage, token);
        setPageFeedback(fb);
      } catch (e) {
        setPageFeedback([]);
      } finally {
        setLoadingPageFeedback(false);
      }
    };
    run();
  }, [projectId, documentId, token, currentPage]);

  // Sorting functionality
  const handleSort = (field: keyof DocumentExtractionJob) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const sortedJobs = [...extractionJobs].sort((a, b) => {
    if (!sortField) return 0;
    
    const aValue = a[sortField as keyof DocumentExtractionJob];
    const bValue = b[sortField as keyof DocumentExtractionJob];
    
    if (aValue === null || aValue === undefined) return 1;
    if (bValue === null || bValue === undefined) return -1;
    
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortDirection === 'asc' 
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    }
    
    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
    }
    
    return 0;
  });

  // Handle annotation click from annotations list (must be before any early returns)
  const handleAnnotationClick = useCallback((pageNumber: number, extractorUuid: string, annotationUuid: string) => {
    // Find the job by UUID to get the extractor name
    const job = extractionJobs.find(j => j.uuid === extractorUuid);
    if (job) {
      // Set flag to prevent auto view mode override
      isNavigatingFromAnnotationClick.current = true;
      setCurrentPage(pageNumber);
      setSelectedExtractor(job.extractor);
      
      // Find the annotation to determine which view mode it belongs to
      const annotation = annotations.find(a => a.uuid === annotationUuid);
      let targetViewMode: ContentViewMode = "text"; // Default fallback
      
      if (annotation) {
        // Get the annotation's text fragment
        const fragment = (annotation.text || '').slice(annotation.selection_start ?? 0, annotation.selection_end ?? 0);
        
        if (fragment) {
          // Get content for the target page to check which view mode contains this fragment
          const pageContentData = pageContent.find(page => page.page_number === pageNumber);
          if (pageContentData) {
            const content = pageContentData.content;
            const info = getContentInfo(content);
            
            // Check if fragment exists in combined view (priority, since annotations can be created there)
            if (info.hasCombined) {
              const combinedText = getContentForViewMode(content, 'combined');
              if (combinedText.includes(fragment)) {
                targetViewMode = 'combined';
              } else if (info.hasText) {
                // If not in combined, check text view
                const textContent = getContentForViewMode(content, 'text');
                if (textContent.includes(fragment)) {
                  targetViewMode = 'text';
                }
              }
            } else if (info.hasText) {
              // No combined view, check text view
              const textContent = getContentForViewMode(content, 'text');
              if (textContent.includes(fragment)) {
                targetViewMode = 'text';
              }
            }
          }
        }
      }
      
      setContentViewMode(targetViewMode);
      setActiveTab("annotation");
      // Highlight the annotation after a short delay to allow the tab to render
      setTimeout(() => {
        setHighlightedAnnotationId(annotationUuid);
        // Clear highlight after 3 seconds
        setTimeout(() => setHighlightedAnnotationId(null), 3000);
      }, 100);
    }
  }, [extractionJobs, annotations, pageContent]);

  // Loading state
  if (authLoading || loading) {
    return (
      <Layout>
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span>{authLoading ? 'Loading authentication...' : 'Loading extraction data...'}</span>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  // Check if user is authenticated
  if (!token) {
    return (
      <Layout>
        <div className="container mx-auto px-6 py-8">
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-6 w-6" />
              <span>Please log in to view extraction data</span>
            </div>
            <Button 
              onClick={retryAuth} 
              variant="outline" 
              className="mt-2"
            >
              Retry Authentication
            </Button>
          </div>
        </div>
      </Layout>
    );
  }

  // Error state
  if (error) {
    return (
      <Layout>
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-6 w-6" />
              <span>Error: {error}</span>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  const contentInfo = getContentInfo(getCurrentPageContent());
  
  // Check if any extractor has Success status
  const hasSuccessfulExtractors = hasSuccessfulExtractor(extractionJobs);
  const isAnnotationTab = activeTab === "annotation";
  const basePadding = "px-6 py-8";
  const annotationWrapperClasses = `w-full max-w-full flex flex-col h-screen overflow-x-hidden`;
  const defaultWrapperClasses = `container mx-auto ${basePadding}`;
  const pageWrapperClass = isAnnotationTab ? annotationWrapperClasses : defaultWrapperClasses;
  const contentTabsClass = isAnnotationTab
    ? "w-full max-w-full flex-1 flex flex-col min-h-0 overflow-hidden"
    : "w-full";
  const annotationContentClass = "mt-0 flex-1 flex flex-col overflow-hidden min-h-0";
  const annotationGridClass = "grid grid-cols-1 lg:grid-cols-2 gap-6 w-full max-w-full flex-1 min-h-0 overflow-hidden";

  // Handle tab change to prevent switching to disabled tabs
  const handleTabChange = (value: string) => {
    if ((value === "annotation" || value === "annotations-list") && !hasSuccessfulExtractors) {
      return; // Don't allow switching to disabled tabs
    }
    setActiveTab(value);
  };

  return (
    <Layout>
      <div className={pageWrapperClass}>
        <div className={isAnnotationTab ? "px-6 pt-8 pb-4 flex-shrink-0 w-full min-w-0" : "mb-6 w-full min-w-0"}>
          <div className="flex items-center gap-6 w-full min-w-0 overflow-hidden">
            <div className="flex items-center gap-4 min-w-0 flex-1 overflow-hidden">
              <Link href={`/pdf/projects/${projectId}`}>
                <Button variant="ghost" size="sm" className="flex-shrink-0">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
              </Link>
              <h1 className="text-3xl font-bold text-foreground truncate min-w-0">
                {doc?.filename || 'Document'}
              </h1>
            </div>
            <Tabs value={activeTab} onValueChange={handleTabChange} className="flex-shrink-0">
              <TabsList>
                <TabsTrigger value="summary">Summary</TabsTrigger>
                <TabsTrigger 
                  value="annotation" 
                  disabled={!hasSuccessfulExtractors}
                  className={!hasSuccessfulExtractors ? "opacity-50 cursor-not-allowed" : ""}
                >
                  Annotation
                </TabsTrigger>
                <TabsTrigger 
                  value="annotations-list" 
                  disabled={!hasSuccessfulExtractors}
                  className={!hasSuccessfulExtractors ? "opacity-50 cursor-not-allowed" : ""}
                >
                  Annotations List
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={handleTabChange} className={contentTabsClass}>
          <TabsContent value="summary">
            <Card>
              <CardHeader>
                <CardTitle className="text-xl font-semibold">Extractor Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <ExtractionJobsTable
                  jobs={sortedJobs}
                  sortField={sortField}
                  sortDirection={sortDirection}
                  onSort={(field) => handleSort(field as keyof DocumentExtractionJob)}
                  onViewExtractor={(extractor) => {
                    setSelectedExtractor(extractor);
                                   setCurrentPage(1);
                                   setActiveTab("annotation");
                                 }}
                  onRetryJob={retryExtractionJob}
                  retryingJobs={retryingJobs}
                  projectId={projectId}
                  documentId={documentId}
                  token={token}
                  ratingFilter={ratingFilter}
                  onRatingFilterChange={setRatingFilter}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="annotation" className={annotationContentClass}>
            {!hasSuccessfulExtractors ? (
              <div className="flex-1 flex items-center justify-center px-6">
                <Card className="w-full max-w-xl">
                  <CardContent className="flex items-center justify-center h-64">
                    <div className="text-center">
                      <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-muted-foreground mb-2">
                        No Successful Extractors Available
                      </h3>
                      <p className="text-muted-foreground">
                        Please wait for at least one extractor to complete successfully before using the annotation features.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className={`${annotationGridClass} px-6 pb-6`}>
                {/* Viewer Panel - PDF only */}
                <div className="border rounded-lg overflow-hidden flex flex-col min-w-0 min-h-0 h-full">
                  <div className="flex-shrink-0">
                    <PageNavigation
                      currentPage={currentPage}
                      totalPages={totalPages}
                      onPageChange={setCurrentPage}
                    />
                  </div>
                  <div className="flex-1 bg-white overflow-auto flex items-center justify-center p-4 min-h-0">
                    <PDFViewer canvasRef={pdfViewerResult.canvasRef} pdfError={pdfViewerResult.pdfError} />
                  </div>
                </div>
                
                {/* Annotation Panel */}
                <div className="border rounded-lg overflow-hidden flex flex-col min-w-0 min-h-0 h-full">
                  <div className="bg-gray-50 px-4 py-3 border-b flex items-center justify-between gap-2 min-w-0 overflow-hidden">
                    <div className="min-w-0">
                      <ExtractorSelector
                        selectedExtractor={selectedExtractor}
                        extractionJobs={extractionJobs}
                        onSelectExtractor={(extractor) => {
                          setSelectedExtractor(extractor);
                        }}
                      />
                    </div>
                    <div className="flex-shrink-0">
                      <ContentViewSelector
                        viewMode={contentViewMode}
                        onViewModeChange={setContentViewMode}
                        hasCombined={contentInfo.hasCombined}
                        hasText={contentInfo.hasText}
                        hasTable={contentInfo.hasTable}
                        hasMarkdown={contentInfo.hasMarkdown}
                        hasLatex={contentInfo.hasLatex}
                        hasImages={contentInfo.hasImages}
                      />
                    </div>
                    <div className="flex-shrink-0">
                      <RatingControl
                        rating={rating}
                        onRatingChange={handleRatingChange}
                        submitting={submittingRating}
                        error={ratingError}
                        averageRating={pageAverageRating?.average_rating}
                        totalRatings={pageAverageRating?.total_ratings}
                      />
                    </div>
                  </div>
                
                  <div className="p-4 flex-1 overflow-y-auto min-h-0">
                    <AnnotationPanel
                      content={getCurrentPageContent()}
                      viewMode={contentViewMode}
                      loading={loadingPageContent}
                      error={pageContentError}
                      annotations={annotations}
                      selectedExtractor={selectedExtractor}
                      extractionJobs={extractionJobs}
                      currentPage={currentPage}
                      documentUuid={doc?.uuid || ''}
                      token={token}
                      onAnnotationsChange={setAnnotations}
                      highlightedAnnotationId={highlightedAnnotationId}
                    />
                  </div>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="annotations-list">
            {!hasSuccessfulExtractors ? (
              <Card>
                <CardContent className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-muted-foreground mb-2">
                      No Successful Extractors Available
                    </h3>
                    <p className="text-muted-foreground">
                      Please wait for at least one extractor to complete successfully before viewing annotations.
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl font-semibold">All Annotations</CardTitle>
                </CardHeader>
                <CardContent>
                  <AnnotationsListTable
                    projectId={projectId}
                    documentId={documentId}
                    token={token}
                    extractionJobs={extractionJobs}
                    onAnnotationClick={handleAnnotationClick}
                  />
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}