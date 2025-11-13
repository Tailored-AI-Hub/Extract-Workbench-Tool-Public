'use client'

import { useParams } from 'next/navigation'
import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import Layout from '../../../../../../components/Layout'
import { useAuth } from '../../../../../../contexts/AuthContext'
import { audioApi, AudioExtractionJob, AudioAnnotation, AudioSegmentAverageRating } from '../../../../../../services/audioApi'
import { API_BASE_URL } from '../../../../../../services/api'
import { useQuery } from '@tanstack/react-query'
import { Tabs, TabsContent } from '../../../../../../components/ui/tabs'
import { Loader2 } from 'lucide-react'
import { useAudioExtractionJobPolling } from '../../../../../hooks/useAudioExtractionJobPolling'
import { AudioExtractorsHeader } from './components/AudioExtractorsHeader'
import { AudioSummaryTab } from './components/AudioSummaryTab'
import { AudioAnnotationTab } from './components/AudioAnnotationTab'
import { AudioAnnotationsListTab } from './components/AudioAnnotationsListTab'
import { toast } from '../../../../../../components/ui/sonner'

export default function AudioExtractorsPage() {
  const params = useParams()
  const projectId = params?.projectId as string
  const audioId = params?.audioId as string
  const { token } = useAuth()

  // UI state
  const [activeTab, setActiveTab] = useState('summary')
  const [selectedExtractor, setSelectedExtractor] = useState<string>('')
  const [currentSegment, setCurrentSegment] = useState(1)
  // Audio only returns text, so viewMode is always 'text'
  const viewMode: 'text' = 'text'
  const [sortField, setSortField] = useState<keyof AudioExtractionJob | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  
  // State for highlighting a specific annotation
  const [highlightedAnnotationId, setHighlightedAnnotationId] = useState<string | null>(null)
  
  // Jobs state
  const [jobs, setJobs] = useState<AudioExtractionJob[]>([])
  const [jobsLoading, setJobsLoading] = useState(true)
  const [retryingJobs, setRetryingJobs] = useState<Set<string>>(new Set())
  
  // Rating state
  const [rating, setRating] = useState(0)
  const [submittingRating, setSubmittingRating] = useState(false)
  const [ratingError, setRatingError] = useState<string | null>(null)
  const [segmentAverageRating, setSegmentAverageRating] = useState<AudioSegmentAverageRating | null>(null)
  
  // Annotations state
  const [annotations, setAnnotations] = useState<AudioAnnotation[]>([])
  const [loadingAnnotations, setLoadingAnnotations] = useState(false)

  // Raw result state for supported extractors (AWS Transcribe, AssemblyAI)
  const [rawResult, setRawResult] = useState<any>(null)
  const [loadingRawResult, setLoadingRawResult] = useState(false)
  const fetchedRawResultJobUuidRef = useRef<string | null>(null)

  // Polling hook for jobs
  const { fetchExtractionJobs } = useAudioExtractionJobPolling(projectId, audioId, token, jobs, setJobs)

  // Initial fetch and setup
  useEffect(() => {
    const fetchJobs = async () => {
      if (!projectId || !audioId || !token) {
        return
      }
      
      try {
        setJobsLoading(true)
        const jobsData = await audioApi.getAudioExtractionJobs(projectId, audioId, token)
        setJobs(jobsData)
      } catch (error) {
        console.error('Failed to fetch audio extraction jobs:', error)
      } finally {
        setJobsLoading(false)
      }
    }

    fetchJobs()
  }, [projectId, audioId, token])

  useEffect(() => {
    if (!selectedExtractor && jobs.length > 0) {
      const successfulJob = jobs.find(j => j.status === 'Success')
      setSelectedExtractor(successfulJob?.extractor || jobs[0].extractor)
    }
  }, [jobs, selectedExtractor])

  const selectedJob = useMemo(() => jobs.find(j => j.extractor === selectedExtractor), [jobs, selectedExtractor])

  const { data: segments = [] } = useQuery({
    queryKey: ['audio-segments', projectId, audioId, selectedJob?.uuid],
    queryFn: () => audioApi.getExtractionJobSegments(projectId, audioId, selectedJob!.uuid, token!),
    enabled: !!token && !!projectId && !!audioId && !!selectedJob?.uuid,
  })

  useEffect(() => {
    if (segments.length > 0 && currentSegment === 1) {
      const firstSegment = segments.find(s => s.segment_number === 1)
      if (firstSegment) setCurrentSegment(1)
    }
  }, [segments, currentSegment])

  const currentContent = useMemo(() => {
    const found = segments.find(s => s.segment_number === currentSegment)
    const content = found?.content || {}
    return content?.COMBINED || content?.TEXT || ''
  }, [segments, currentSegment])

  // Check if segments have timestamps (chunked mode)
  const hasChunks = segments.some(s => s.start_ms !== null && s.start_ms !== undefined && s.end_ms !== null && s.end_ms !== undefined)

  // Fetch annotations for current segment
  useEffect(() => {
    const fetchAnnotations = async () => {
      if (!token || !audioId || !selectedJob?.uuid) return
      
      try {
        setLoadingAnnotations(true)
        const annos = await audioApi.getAudioAnnotations(audioId, token, selectedJob.uuid, currentSegment)
        setAnnotations(annos)
      } catch (err) {
        console.error('Error fetching annotations:', err)
      } finally {
        setLoadingAnnotations(false)
      }
    }
    fetchAnnotations()
  }, [token, audioId, selectedJob?.uuid, currentSegment])

  // Fetch average rating for current segment
  const fetchSegmentAverageRating = useCallback(async () => {
    if (!token || !projectId || !audioId || !selectedJob?.uuid) return
    
    try {
      const avgRating = await audioApi.getAudioSegmentAverageRating(
        projectId,
        audioId,
        currentSegment,
        selectedJob.uuid,
        token
      )
      setSegmentAverageRating(avgRating)
      const userRating = avgRating.user_rating || 0
      setRating(userRating)
    } catch (error) {
      console.error('Error fetching average rating:', error)
      setSegmentAverageRating(null)
      setRating(0)
    }
  }, [token, projectId, audioId, currentSegment, selectedJob?.uuid])

  useEffect(() => {
    fetchSegmentAverageRating()
  }, [fetchSegmentAverageRating])

  // Fetch raw result for supported extractors (AWS Transcribe, AssemblyAI)
  useEffect(() => {
    const fetchRawResult = async () => {
      const supportedExtractors = ['aws-transcribe', 'assemblyai']
      if (!selectedJob || !supportedExtractors.includes(selectedJob.extractor) || !token || selectedJob.status !== 'Success') {
        // Only clear if we switched away from supported extractors
        if (!selectedJob || !supportedExtractors.includes(selectedJob.extractor)) {
          setRawResult(null)
          fetchedRawResultJobUuidRef.current = null
        }
        return
      }
      
      // Only fetch if job UUID changed (prevents refetch on polling updates)
      if (fetchedRawResultJobUuidRef.current === selectedJob.uuid) {
        return
      }
      
      try {
        setLoadingRawResult(true)
        const result = await audioApi.getAudioExtractionRawResult(
          projectId,
          audioId,
          selectedJob.uuid,
          token
        )
        setRawResult(result)
        fetchedRawResultJobUuidRef.current = selectedJob.uuid
      } catch (error) {
        console.error('Error fetching raw result:', error)
        setRawResult(null)
        fetchedRawResultJobUuidRef.current = null
      } finally {
        setLoadingRawResult(false)
      }
    }

    fetchRawResult()
  }, [projectId, audioId, selectedJob, token])

  // Helper function to format raw result text (same logic as FormattedRawResult)
  const formatRawResultText = useCallback((data: any, extractor: string): string => {
    if (!data) return ''

    if (extractor === 'assemblyai') {
      let result = ''
      if (data.text) {
        result += 'text:\n'
        result += `${data.text}\n\n`
      }
      if (data.words && Array.isArray(data.words) && data.words.length > 0) {
        result += 'words:\n'
        data.words.forEach((word: any, index: number) => {
          result += `  ${index + 1}.\n`
          result += `    text: ${word.text || ''}\n`
          result += `    start: ${word.start !== undefined ? word.start : 'N/A'}\n`
          result += `    end: ${word.end !== undefined ? word.end : 'N/A'}\n`
          result += `    confidence: ${word.confidence !== undefined ? word.confidence : 'N/A'}\n`
          if (index < data.words.length - 1) {
            result += '\n'
          }
        })
      }
      return result
    } else if (extractor === 'aws-transcribe') {
      let result = ''
      const results = data.results || {}
      if (results.text && Array.isArray(results.text)) {
        result += 'text:\n'
        results.text.forEach((transcript: any, index: number) => {
          result += `  ${index + 1}.\n`
          result += `    transcript: ${transcript.transcript || ''}\n`
          if (index < results.text.length - 1) {
            result += '\n'
          }
        })
        result += '\n'
      }
      if (results.items && Array.isArray(results.items)) {
        result += 'items:\n'
        results.items.forEach((item: any, index: number) => {
          if (item.alternatives && Array.isArray(item.alternatives)) {
            const altStrings = item.alternatives.map((alt: any) => {
              const confidence = alt.confidence !== undefined ? alt.confidence : 'N/A'
              const content = alt.content || ''
              const startTime = item.start_time !== undefined ? item.start_time : 'N/A'
              const endTime = item.end_time !== undefined ? item.end_time : 'N/A'
              return `{"confidence": "${confidence}", "content": "${content}", "start_time": "${startTime}", "end_time": "${endTime}"}`
            })
            result += `  ${altStrings.join(', ')}\n`
          } else {
            // If no alternatives, still show start_time and end_time
            const startTime = item.start_time !== undefined ? item.start_time : 'N/A'
            const endTime = item.end_time !== undefined ? item.end_time : 'N/A'
            result += `  {"start_time": "${startTime}", "end_time": "${endTime}"}\n`
          }
        })
      }
      return result
    } else if (extractor === 'whisper-openai') {
      // Format segments for Whisper
      if (Array.isArray(data)) {
        let result = ''
        const fullText = data
          .map((seg: any) => {
            const content = seg.content || {}
            return content.COMBINED || content.TEXT || ''
          })
          .filter((text: string) => text.trim())
          .join(' ')
        
        if (fullText) {
          result += 'text:\n'
          result += `${fullText}\n\n`
        }
        
        if (data.length > 0) {
          result += 'segments:\n'
          data.forEach((seg: any, index: number) => {
            const content = seg.content || {}
            const metadata = seg.metadata || {}
            const text = content.COMBINED || content.TEXT || ''
            
            // Skip empty segments (unless explicitly marked as empty)
            if (!text.trim() && !metadata.is_empty && !seg.start_ms && !seg.end_ms) return
            
            // Get start_ms and end_ms from top-level or metadata
            const startMs = seg.start_ms !== undefined ? seg.start_ms : (metadata.start_ms !== undefined ? metadata.start_ms : null)
            const endMs = seg.end_ms !== undefined ? seg.end_ms : (metadata.end_ms !== undefined ? metadata.end_ms : null)
            const language = metadata.language || seg.language
            
            result += `  ${index + 1}.\n`
            result += `    text: ${text}\n`
            result += `    start: ${startMs !== undefined && startMs !== null ? startMs : 'N/A'}\n`
            result += `    end: ${endMs !== undefined && endMs !== null ? endMs : 'N/A'}\n`
            if (language) {
              result += `    language: ${language}\n`
            }
            if (index < data.length - 1) {
              result += '\n'
            }
          })
        }
        return result
      }
      return JSON.stringify(data, null, 2)
    }
    return JSON.stringify(data, null, 2)
  }, [])

  // Get formatted text for annotation mapping
  const formattedText = useMemo(() => {
    if (!selectedExtractor) return ''
    // For Whisper, use segments instead of rawResult
    if (selectedExtractor === 'whisper-openai') {
      if (!segments || segments.length === 0) return ''
      return formatRawResultText(segments, selectedExtractor)
    }
    if (!rawResult) return ''
    return formatRawResultText(rawResult, selectedExtractor)
  }, [rawResult, selectedExtractor, formatRawResultText, segments])

  // Map annotations to formatted text positions - EXACT SAME LOGIC AS DOCUMENT ANNOTATIONS
  const mappedAnnotations = useMemo(() => {
    if (!formattedText) return []
    
    // Filter annotations for current segment/job (same as document filters by page/job)
    const filteredAnnotations = selectedExtractor === 'whisper-openai' 
      ? annotations.filter(a => a.extraction_job_uuid === selectedJob?.uuid)
      : annotations.filter(a => a.segment_number === currentSegment && a.extraction_job_uuid === selectedJob?.uuid)
    
    // Use stored character positions directly (no text matching needed)
    return filteredAnnotations.map(a => {
      if (a.selection_start_char != null && a.selection_end_char != null) {
        const start = Math.max(0, Math.min(a.selection_start_char, formattedText.length))
        const end = Math.max(start, Math.min(a.selection_end_char, formattedText.length))
        return { id: a.uuid, start, end, comment: a.comment || '' }
      }
      
      // Fallback for old annotations without selection positions
      return { id: a.uuid, start: 0, end: 0, comment: a.comment || '' }
    })
  }, [annotations, currentSegment, formattedText, selectedExtractor, selectedJob?.uuid])

  const handleCreateAnnotation = useCallback(async ({ start, end, comment, formattedText: displayedText }: { start: number; end: number; comment: string; formattedText?: string }) => {
    if (!audioId || !token || !selectedJob) {
      console.error('Missing required data for annotation creation:', { audioId, token: !!token, selectedJob: !!selectedJob })
      return
    }

    // Use the formattedText from FormattedRawResult if provided, otherwise fallback to parent's formattedText
    const textSource = displayedText || formattedText
    if (!textSource) {
      console.error('No formatted text available for annotation')
      return
    }

    // EXACT SAME PATTERN AS DOCUMENT ANNOTATIONS (lines 128-144 of AnnotationPanel.tsx)
    // Store FULL formatted text (not just selected text) and character positions
    const selectedText = textSource.substring(start, end)
    if (!selectedText.trim()) {
      console.warn('No text selected for annotation')
      return
    }

    // For Whisper, try to find which segment the text belongs to
    let segmentNum = currentSegment
    if (selectedExtractor === 'whisper-openai' && segments) {
      const matchingSegment = (segments as any[]).find((seg: any) => {
        const content = seg.content?.COMBINED || seg.content?.TEXT || ''
        return content.includes(selectedText.trim())
      })
      if (matchingSegment) {
        segmentNum = matchingSegment.segment_number
      }
    }

    try {
      // Store like document annotations:
      // - text: FULL formatted text being displayed
      // - selectionStartChar/selectionEndChar: character positions within that text
      const payload = {
        audioId: audioId,
        extractionJobUuid: selectedJob.uuid,
        segmentNumber: segmentNum,
        text: textSource, // Store FULL formatted text (like currentText in documents)
        comment: comment || '', // Comment for user notes
        selectionStartChar: start, // Character position start
        selectionEndChar: end,     // Character position end
      }

      const created = await audioApi.createAudioAnnotation(payload, token!)

      setAnnotations([...annotations, created])
      return { id: created.uuid }
    } catch (error) {
      console.error('Error creating annotation:', error)
      throw error
    }
  }, [audioId, token, selectedJob, formattedText, currentSegment, selectedExtractor, segments, annotations])

  const handleDeleteAnnotation = useCallback(async (id: string) => {
    if (!token) {
      console.error('No token available for annotation deletion')
      return
    }
    try {
      await audioApi.deleteAudioAnnotation(id, token)
      setAnnotations(annotations.filter(a => a.uuid !== id))
    } catch (error) {
      console.error('Error deleting annotation:', error)
      throw error
    }
  }, [token, annotations])

  // Handle rating change
  const handleRatingChange = async (newRating: number) => {
    if (!token || !projectId || !audioId || !selectedJob) return
    const previous = rating
    setRating(newRating)
    setRatingError(null)
    setSubmittingRating(true)
    
    try {
      await audioApi.submitAudioSegmentFeedback({
        audio_uuid: audioId,
        segment_number: currentSegment,
        extraction_job_uuid: selectedJob.uuid,
        rating: newRating,
        comment: ''
      }, projectId, token)
      
      // Refresh average rating for current segment
      await fetchSegmentAverageRating()
      
      // Refresh extraction jobs to update total_rating in summary table
      await fetchExtractionJobs()
    } catch (e) {
      setRating(previous)
      setRatingError(e instanceof Error ? e.message : 'Failed to submit rating')
    } finally {
      setSubmittingRating(false)
    }
  }

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

  const onSort = (field: keyof AudioExtractionJob) => {
    setSortField(prev => (prev === field ? field : field))
    setSortDirection(prev => (sortField === field ? (prev === 'asc' ? 'desc' : 'asc') : 'asc'))
  }

  // Retry extraction job
  const retryExtractionJob = useCallback(async (jobUuid: string) => {
    if (!projectId || !audioId || !token) {
      return
    }

    try {
      setRetryingJobs(prev => new Set(prev).add(jobUuid))
      
      await audioApi.retryExtractionJob(projectId, audioId, jobUuid, token)
      
      // Refresh extraction jobs using the polling hook's fetch function
      await fetchExtractionJobs()
      
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
  }, [projectId, audioId, token, fetchExtractionJobs])

  // Handle annotation click from annotations list
  const handleAnnotationClick = useCallback((segmentNumber: number, extractorUuid: string, annotationUuid: string) => {
    const job = jobs.find(j => j.uuid === extractorUuid)
    if (job) {
      setCurrentSegment(segmentNumber)
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

  const audioUrl = useMemo(() => {
    if (!token || !projectId || !audioId) return ''
    // Note: Browser will handle the auth token from the session automatically
    return `${API_BASE_URL}/audio/projects/${projectId}/audios/${audioId}/audio-load`
  }, [projectId, audioId, token])

  // Get audio filename
  const { data: audioItem } = useQuery({
    queryKey: ['audio-item', projectId, audioId],
    queryFn: async () => {
      const audios = await audioApi.getProjectAudios(projectId, token!, 1, 1000)
      return audios.audios.find(a => a.uuid === audioId)
    },
    enabled: !!token && !!projectId && !!audioId,
  })

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
          <AudioExtractorsHeader
            projectId={projectId}
            filename={audioItem?.filename}
            activeTab={activeTab}
            hasSuccessfulExtractors={hasSuccessfulExtractors}
            onTabChange={handleTabChange}
          />
        </div>

        <Tabs value={activeTab} onValueChange={handleTabChange} className={contentTabsClass}>
          <TabsContent value="summary">
            <AudioSummaryTab
              sortedJobs={sortedJobs}
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={onSort as (field: keyof AudioExtractionJob) => void}
              projectId={projectId}
              audioId={audioId}
              token={token}
              onViewExtractor={(extractor: string) => {
                setSelectedExtractor(extractor)
                setCurrentSegment(1)
                setActiveTab('annotation')
              }}
              onRetryJob={retryExtractionJob}
              retryingJobs={retryingJobs}
            />
          </TabsContent>

          <TabsContent value="annotation" className={annotationContentClass}>
            <AudioAnnotationTab
              hasSuccessfulExtractors={hasSuccessfulExtractors}
              audioUrl={audioUrl}
              token={token}
              selectedExtractor={selectedExtractor}
              setSelectedExtractor={setSelectedExtractor}
              jobs={jobs}
              rating={rating}
              onRatingChange={handleRatingChange}
              submittingRating={submittingRating}
              ratingError={ratingError}
              averageRating={segmentAverageRating?.average_rating ?? undefined}
              totalRatings={segmentAverageRating?.total_ratings ?? undefined}
              segments={segments}
              loadingRawResult={loadingRawResult}
              rawResult={rawResult}
              formattedText={formattedText}
              mappedAnnotations={mappedAnnotations}
              onCreateAnnotation={handleCreateAnnotation}
              onDeleteAnnotation={handleDeleteAnnotation}
              hasChunks={hasChunks}
              loadingAnnotations={loadingAnnotations}
              annotations={annotations}
              currentContent={currentContent}
              currentSegment={currentSegment}
              audioId={audioId}
              onAnnotationsChange={setAnnotations}
              highlightedAnnotationId={highlightedAnnotationId}
            />
          </TabsContent>

          <TabsContent value="annotations-list">
            <AudioAnnotationsListTab
              hasSuccessfulExtractors={hasSuccessfulExtractors}
              projectId={projectId}
              audioId={audioId}
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


