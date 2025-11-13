'use client'

import { useParams } from 'next/navigation'
import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import Layout from '../../../../../../components/Layout'
import { useAuth } from '../../../../../../contexts/AuthContext'
import { imageApi, ImageExtractionJob, ImageAnnotation, ImageAverageRating, ImageContent } from '../../../../../../services/imageApi'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Tabs, TabsContent } from '../../../../../../components/ui/tabs'
import { Loader2 } from 'lucide-react'
import { useImageExtractionJobPolling } from '../../../../../hooks/useImageExtractionJobPolling'
import { ImageExtractorsHeader } from './components/ImageExtractorsHeader'
import { ImageSummaryTab } from './components/ImageSummaryTab'
import { ImageAnnotationTab } from './components/ImageAnnotationTab'
import { ImageAnnotationsListTab } from './components/ImageAnnotationsListTab'
import { toast } from '../../../../../../components/ui/sonner'

export default function ImageExtractorsPage() {
  const params = useParams()
  const projectId = params?.projectId as string
  const imageId = params?.imageId as string
  const { token } = useAuth()
  const queryClient = useQueryClient()

  // UI state
  const [activeTab, setActiveTab] = useState('summary')
  const [selectedExtractor, setSelectedExtractor] = useState<string>('')
  const [sortField, setSortField] = useState<keyof ImageExtractionJob | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  
  // Jobs state
  const [jobs, setJobs] = useState<ImageExtractionJob[]>([])
  const [jobsLoading, setJobsLoading] = useState(true)
  const [retryingJobs, setRetryingJobs] = useState<Set<string>>(new Set())
  
  // Rating state
  const [rating, setRating] = useState(0)
  const [submittingRating, setSubmittingRating] = useState(false)
  const [ratingError, setRatingError] = useState<string | null>(null)
  
  // Annotations state
  const [annotations, setAnnotations] = useState<ImageAnnotation[]>([])
  const [loadingAnnotations, setLoadingAnnotations] = useState(false)

  // Image file state
  const [imageUrl, setImageUrl] = useState<string>('')
  const [imageLoading, setImageLoading] = useState(true)
  const [imageError, setImageError] = useState<string | null>(null)
  const imageUrlRef = useRef<string>('')

  // Polling hook for jobs
  const { fetchExtractionJobs } = useImageExtractionJobPolling(projectId, imageId, token, jobs, setJobs)

  // Initial fetch and setup
  useEffect(() => {
    const fetchJobs = async () => {
      if (!projectId || !imageId || !token) {
        return
      }
      
      try {
        setJobsLoading(true)
        const jobsData = await imageApi.getImageExtractionJobs(projectId, imageId, token)
        setJobs(jobsData)
      } catch (error) {
        console.error('Failed to fetch image extraction jobs:', error)
      } finally {
        setJobsLoading(false)
      }
    }

    fetchJobs()
  }, [projectId, imageId, token])

  useEffect(() => {
    if (!selectedExtractor && jobs.length > 0) {
      const successfulJob = jobs.find(j => j.status === 'Success')
      setSelectedExtractor(successfulJob?.extractor || jobs[0].extractor)
    }
  }, [jobs, selectedExtractor])

  const selectedJob = useMemo(() => jobs.find(j => j.extractor === selectedExtractor), [jobs, selectedExtractor])

  // Fetch image data
  const { data: image } = useQuery({
    queryKey: ['image', projectId, imageId],
    queryFn: () => imageApi.getImage(projectId, imageId, token!),
    enabled: !!token && !!projectId && !!imageId,
  })

  // Fetch content
  const { data: content, isLoading: contentLoading } = useQuery<ImageContent>({
    queryKey: ['image-content', projectId, imageId, selectedJob?.uuid],
    queryFn: () => imageApi.getImageExtractionContent(projectId, imageId, selectedJob!.uuid, token!),
    enabled: !!token && !!projectId && !!imageId && !!selectedJob?.uuid && selectedJob?.status === 'Success',
  })

  // Fetch annotations
  useEffect(() => {
    const fetchAnnotations = async () => {
      if (!token || !imageId || !selectedJob?.uuid) {
        setAnnotations([])
        return
      }
      
      try {
        setLoadingAnnotations(true)
        const data = await imageApi.getImageAnnotations(imageId, token, selectedJob.uuid)
        setAnnotations(data)
      } catch (error) {
        console.error('Failed to fetch annotations:', error)
      } finally {
        setLoadingAnnotations(false)
      }
    }

    fetchAnnotations()
  }, [token, imageId, selectedJob?.uuid])

  // Fetch average rating
  const { data: averageRating } = useQuery<ImageAverageRating>({
    queryKey: ['image-average-rating', projectId, imageId, selectedJob?.uuid],
    queryFn: () => imageApi.getImageAverageRating(projectId, imageId, selectedJob!.uuid, token!),
    enabled: !!token && !!projectId && !!imageId && !!selectedJob?.uuid,
  })

  useEffect(() => {
    if (averageRating) {
      setRating(averageRating.user_rating || 0)
    }
  }, [averageRating])

  // Load image file
  useEffect(() => {
    const loadImage = async () => {
      if (!image || !token) return
      try {
        setImageLoading(true)
        setImageError(null)
        // Cleanup previous URL if exists
        if (imageUrlRef.current) {
          URL.revokeObjectURL(imageUrlRef.current)
          imageUrlRef.current = ''
        }
        const blob = await imageApi.downloadImageFile(projectId, imageId, token)
        const url = URL.createObjectURL(blob)
        imageUrlRef.current = url
        setImageUrl(url)
      } catch (error) {
        console.error('Failed to load image:', error)
        setImageError('Failed to load image file.')
      } finally {
        setImageLoading(false)
      }
    }
    loadImage()

    return () => {
      // Cleanup: revoke object URL when component unmounts or dependencies change
      if (imageUrlRef.current) {
        URL.revokeObjectURL(imageUrlRef.current)
        imageUrlRef.current = ''
      }
    }
  }, [image, projectId, imageId, token])

  // Get current text content - prioritize TEXT (uppercase) as that's what extractors return
  const currentText = useMemo(() => {
    if (!content) return ''
    const contentData = content.content || {}
    // Prioritize TEXT (what extractors return) over text (lowercase)
    return contentData.TEXT || contentData.text || JSON.stringify(contentData, null, 2)
  }, [content])

  // Map annotations to text positions
  const mappedAnnotations = useMemo(() => {
    if (!currentText || !selectedJob) return []
    
    const filteredAnnotations = annotations.filter(a => a.extraction_job_uuid === selectedJob.uuid)
    
    return filteredAnnotations.map(a => {
      // If we have stored character positions, try to use them directly
      if (a.selection_start_char != null && a.selection_end_char != null) {
        // First, try using the stored positions directly
        const storedText = a.text || ''
        const storedStart = a.selection_start_char
        const storedEnd = a.selection_end_char
        
        // Check if the stored text matches the current text
        if (storedText === currentText) {
          // Text matches, use stored positions directly
          const start = Math.max(0, Math.min(storedStart, currentText.length))
          const end = Math.max(start, Math.min(storedEnd, currentText.length))
          return { id: a.uuid, start, end, comment: a.comment || '' }
        } else {
          // Text doesn't match, try to find the fragment in current text
          const fragment = storedText.slice(storedStart, storedEnd)
          if (fragment && fragment.trim()) {
            // Try exact match first
            let idx = currentText.indexOf(fragment)
            if (idx >= 0) {
              return { id: a.uuid, start: idx, end: idx + fragment.length, comment: a.comment || '' }
            }
            // Try case-insensitive match
            idx = currentText.toLowerCase().indexOf(fragment.toLowerCase())
            if (idx >= 0) {
              return { id: a.uuid, start: idx, end: idx + fragment.length, comment: a.comment || '' }
            }
            // Try to find a substring that matches (for whitespace differences)
            const normalizedFragment = fragment.replace(/\s+/g, ' ').trim()
            const normalizedCurrent = currentText.replace(/\s+/g, ' ')
            idx = normalizedCurrent.indexOf(normalizedFragment)
            if (idx >= 0) {
              // Map back to original text positions
              let originalIdx = 0
              let normalizedIdx = 0
              while (normalizedIdx < idx && originalIdx < currentText.length) {
                if (/\s/.test(currentText[originalIdx])) {
                  // Skip whitespace in original
                  originalIdx++
                  while (originalIdx < currentText.length && /\s/.test(currentText[originalIdx])) {
                    originalIdx++
                  }
                } else {
                  originalIdx++
                }
                normalizedIdx++
              }
              return { id: a.uuid, start: originalIdx, end: originalIdx + fragment.length, comment: a.comment || '' }
            }
          }
          // Fallback: use stored positions anyway (might be slightly off)
          const start = Math.max(0, Math.min(storedStart, currentText.length))
          const end = Math.max(start, Math.min(storedEnd, currentText.length))
          return { id: a.uuid, start, end, comment: a.comment || '' }
        }
      }
      
      // No stored positions, try to find the text in current text
      const annotationText = a.text || ''
      if (annotationText) {
        const idx = currentText.indexOf(annotationText)
        if (idx >= 0) {
          return { id: a.uuid, start: idx, end: idx + annotationText.length, comment: a.comment || '' }
        }
      }
      
      return { id: a.uuid, start: 0, end: 0, comment: a.comment || '' }
    }).filter(a => a.start < a.end) // Filter out invalid annotations (start must be less than end)
  }, [annotations, currentText, selectedJob])

  // Handle annotation creation
  const handleCreateAnnotation = useCallback(async ({ start, end, comment }: { start: number; end: number; comment: string }) => {
    if (!imageId || !token || !selectedJob) {
      console.error('Missing required data for annotation creation')
      return
    }

    const selectedText = currentText.substring(start, end)
    if (!selectedText.trim()) {
      console.warn('No text selected for annotation')
      return
    }

    try {
      const payload = {
        imageId,
        extractionJobUuid: selectedJob.uuid,
        text: currentText, // Store FULL text
        comment: comment || '',
        selectionStartChar: start,
        selectionEndChar: end,
      }

      const created = await imageApi.createImageAnnotation(payload, token!)
      // Refetch annotations to ensure we have the latest data
      const updatedAnnotations = await imageApi.getImageAnnotations(imageId, token, selectedJob.uuid)
      setAnnotations(updatedAnnotations)
      queryClient.invalidateQueries({ queryKey: ['image-annotations', imageId, selectedJob.uuid] })
      toast.success('Annotation created')
      return { id: created.uuid }
    } catch (error) {
      console.error('Error creating annotation:', error)
      toast.error('Failed to create annotation')
      throw error
    }
  }, [imageId, token, selectedJob, currentText, queryClient])

  // Handle annotation deletion
  const handleDeleteAnnotation = useCallback(async (id: string) => {
    if (!token || !imageId || !selectedJob) {
      console.error('No token available for annotation deletion')
      return
    }
    try {
      await imageApi.deleteImageAnnotation(id, token)
      // Refetch annotations to ensure we have the latest data
      const updatedAnnotations = await imageApi.getImageAnnotations(imageId, token, selectedJob.uuid)
      setAnnotations(updatedAnnotations)
      queryClient.invalidateQueries({ queryKey: ['image-annotations', imageId, selectedJob.uuid] })
      toast.success('Annotation deleted')
    } catch (error) {
      console.error('Error deleting annotation:', error)
      toast.error('Failed to delete annotation')
      throw error
    }
  }, [token, imageId, selectedJob, queryClient])

  // Handle rating change
  const handleRatingChange = async (newRating: number) => {
    if (!token || !projectId || !imageId || !selectedJob) return
    const previous = rating
    setRating(newRating)
    setRatingError(null)
    setSubmittingRating(true)
    
    try {
      await imageApi.submitImageFeedback(
        projectId,
        imageId,
        {
          image_uuid: imageId,
          extraction_job_uuid: selectedJob.uuid,
          rating: newRating,
        },
        token
      )
      
      // Refresh average rating
      queryClient.invalidateQueries({ queryKey: ['image-average-rating', projectId, imageId, selectedJob.uuid] })
      
      // Refresh extraction jobs to update total_rating in summary table
      queryClient.invalidateQueries({ queryKey: ['image-extraction-jobs', projectId, imageId] })
    } catch (e) {
      setRating(previous)
      setRatingError(e instanceof Error ? e.message : 'Failed to submit rating')
    } finally {
      setSubmittingRating(false)
    }
  }

  // State for highlighting a specific annotation (must be before any early returns)
  const [highlightedAnnotationId, setHighlightedAnnotationId] = useState<string | null>(null)

  // Handle annotation click from annotations list (must be before any early returns)
  const handleAnnotationClick = useCallback((extractorUuid: string, annotationUuid: string) => {
    const job = jobs.find(j => j.uuid === extractorUuid)
    if (job) {
      setSelectedExtractor(job.extractor)
      setActiveTab('annotation')
      // Highlight the annotation after a short delay to allow the tab to render
      setTimeout(() => {
        setHighlightedAnnotationId(annotationUuid)
        // Clear highlight after 3 seconds
        setTimeout(() => setHighlightedAnnotationId(null), 3000)
      }, 100)
    }
  }, [jobs])

  // Sort jobs
  const sortedJobs = useMemo(() => {
    if (!sortField) return jobs
    const copy = [...jobs]
    copy.sort((a: any, b: any) => {
      const av = a[sortField as any]
      const bv = b[sortField as any]
      if (av == null) return 1
      if (bv == null) return -1
      if (typeof av === 'string') return sortDirection === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
      if (typeof av === 'number') return sortDirection === 'asc' ? av - bv : bv - av
      return 0
    })
    return copy
  }, [jobs, sortField, sortDirection])

  const onSort = (field: keyof ImageExtractionJob) => {
    setSortField(prev => (prev === field ? field : field))
    setSortDirection(prev => (sortField === field ? (prev === 'asc' ? 'desc' : 'asc') : 'asc'))
  }

  // Retry extraction job
  const retryExtractionJob = useCallback(async (jobUuid: string) => {
    if (!projectId || !imageId || !token) {
      return
    }

    try {
      setRetryingJobs(prev => new Set(prev).add(jobUuid))
      
      await imageApi.retryExtractionJob(projectId, imageId, jobUuid, token)
      
      // Refresh extraction jobs
      const jobsData = await imageApi.getImageExtractionJobs(projectId, imageId, token)
      setJobs(jobsData)
      
      toast.success('Extraction job retry initiated')
    } catch (error) {
      console.error('Failed to retry extraction job:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to retry extraction job')
    } finally {
      setRetryingJobs(prev => {
        const newSet = new Set(prev)
        newSet.delete(jobUuid)
        return newSet
      })
    }
  }, [projectId, imageId, token])

  // Loading state
  if (jobsLoading) {
    return (
      <Layout>
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span>Loading extraction data...</span>
            </div>
          </div>
        </div>
      </Layout>
    )
  }

  // Check if any extractor has Success status
  const hasSuccessfulExtractors = jobs.some(job => job.status === 'Success')
  const isAnnotationTab = activeTab === 'annotation'

  // Handle tab change to prevent switching to disabled tabs
  const handleTabChange = (value: string) => {
    if ((value === 'annotation' || value === 'annotations-list') && !hasSuccessfulExtractors) {
      return
    }
    setActiveTab(value)
  }

  const basePadding = "px-6 py-8"
  const annotationWrapperClasses = `w-full max-w-full flex flex-col h-screen overflow-x-hidden`
  const defaultWrapperClasses = `container mx-auto ${basePadding}`
  const pageWrapperClass = isAnnotationTab ? annotationWrapperClasses : defaultWrapperClasses
  const contentTabsClass = isAnnotationTab
    ? "w-full max-w-full flex-1 flex flex-col min-h-0 overflow-hidden"
    : "w-full"
  const annotationContentClass = "mt-0 flex-1 flex flex-col overflow-hidden min-h-0"

  return (
    <Layout>
      <div className={pageWrapperClass}>
        <div className={isAnnotationTab ? "px-6 pt-8 pb-4 flex-shrink-0 w-full min-w-0" : "mb-6 w-full min-w-0"}>
          <ImageExtractorsHeader
            projectId={projectId}
            filename={image?.filename}
            activeTab={activeTab}
            hasSuccessfulExtractors={hasSuccessfulExtractors}
            onTabChange={handleTabChange}
          />
        </div>

        <Tabs value={activeTab} onValueChange={handleTabChange} className={contentTabsClass}>
          <TabsContent value="summary">
            <ImageSummaryTab
              sortedJobs={sortedJobs}
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={onSort as (field: keyof ImageExtractionJob) => void}
              projectId={projectId}
              imageId={imageId}
              token={token}
              onViewExtractor={(extractor: string) => {
                setSelectedExtractor(extractor)
                setActiveTab('annotation')
              }}
              onRetryJob={retryExtractionJob}
              retryingJobs={retryingJobs}
            />
          </TabsContent>

          <TabsContent value="annotation" className={annotationContentClass}>
            <ImageAnnotationTab
              hasSuccessfulExtractors={hasSuccessfulExtractors}
              imageUrl={imageUrl}
              imageLoading={imageLoading}
              imageError={imageError}
              imageFilename={image?.filename}
              token={token}
              selectedExtractor={selectedExtractor}
              setSelectedExtractor={setSelectedExtractor}
              jobs={jobs}
              rating={rating}
              onRatingChange={handleRatingChange}
              submittingRating={submittingRating}
              ratingError={ratingError}
              averageRating={averageRating?.average_rating ?? undefined}
              totalRatings={averageRating?.total_ratings ?? undefined}
              content={currentText}
              contentLoading={contentLoading}
              mappedAnnotations={mappedAnnotations}
              onCreateAnnotation={handleCreateAnnotation}
              onDeleteAnnotation={handleDeleteAnnotation}
              loadingAnnotations={loadingAnnotations}
              highlightedAnnotationId={highlightedAnnotationId}
            />
          </TabsContent>

          <TabsContent value="annotations-list">
            <ImageAnnotationsListTab
              hasSuccessfulExtractors={hasSuccessfulExtractors}
              projectId={projectId}
              imageId={imageId}
              token={token}
              jobs={jobs}
              onAnnotationClick={handleAnnotationClick}
            />
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  )
}
