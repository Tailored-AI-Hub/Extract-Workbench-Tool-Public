'use client'

import React from 'react'
import { Card, CardContent } from '../../../../../../../components/ui/card'
import { AlertCircle, Loader2 } from 'lucide-react'
import { AudioPlayer } from '../../../../../../components/AudioPlayer'
import { ExtractorSelector } from '../../../../../../../pdf/components/extractors/ExtractorSelector'
import { RatingControl } from '../../../../../../../pdf/components/extractors/RatingControl'
import { AudioExtractionJob, AudioAnnotation } from '../../../../../../../services/audioApi'
import { FormattedRawResult } from '../../../../../../components/FormattedRawResult'
import { AudioChunkedContent } from '../../../../../../components/AudioChunkedContent'
import { formatAudioExtractorName } from '../../../../../../utils'

interface AudioAnnotationTabProps {
  hasSuccessfulExtractors: boolean
  audioUrl: string
  token: string | null
  selectedExtractor: string
  setSelectedExtractor: (extractor: string) => void
  jobs: AudioExtractionJob[]
  rating: number
  onRatingChange: (rating: number) => void
  submittingRating: boolean
  ratingError: string | null
  averageRating?: number
  totalRatings?: number
  segments: any[]
  loadingRawResult: boolean
  rawResult: any
  formattedText: string
  mappedAnnotations: Array<{ id: string; start: number; end: number; comment: string }>
  onCreateAnnotation: (args: { start: number; end: number; comment: string; formattedText?: string }) => Promise<{ id?: string } | void>
  onDeleteAnnotation: (id: string) => Promise<void>
  hasChunks: boolean
  loadingAnnotations: boolean
  annotations: AudioAnnotation[]
  currentContent: any
  currentSegment: number
  audioId: string
  onAnnotationsChange: (annotations: AudioAnnotation[]) => void
  highlightedAnnotationId?: string | null
}

export function AudioAnnotationTab({
  hasSuccessfulExtractors,
  audioUrl,
  token,
  selectedExtractor,
  setSelectedExtractor,
  jobs,
  rating,
  onRatingChange,
  submittingRating,
  ratingError,
  averageRating,
  totalRatings,
  segments,
  loadingRawResult,
  rawResult,
  formattedText,
  mappedAnnotations,
  onCreateAnnotation,
  onDeleteAnnotation,
  hasChunks,
  loadingAnnotations,
  annotations,
  currentContent,
  currentSegment,
  audioId,
  onAnnotationsChange,
  highlightedAnnotationId
}: AudioAnnotationTabProps) {
  const selectedJob = jobs.find(job => job.extractor === selectedExtractor)
  if (!hasSuccessfulExtractors) {
    return (
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
    )
  }

  return (
    <div className="px-6 pb-6 flex-1 min-h-0 overflow-hidden">
      <Card className="overflow-hidden flex flex-col h-full">
        {/* Header: Audio Player + Controls */}
        <div className="bg-gray-50 px-4 py-3 border-b flex items-center justify-between gap-2 min-w-0 overflow-hidden">
          {/* Audio Title */}
          <div className="flex-shrink-0 mr-4">
            <h3 className="text-sm font-semibold text-foreground truncate max-w-[200px]" title="Audio File">
              Audio File
            </h3>
          </div>
          {/* Audio Player */}
          <div className="min-w-0 flex-1">
            <AudioPlayer src={audioUrl} token={token} className="w-full max-w-80" />
          </div>
          {/* Extractor Selector */}
          <div className="flex-shrink-0">
            <ExtractorSelector
              extractionJobs={jobs as any}
              selectedExtractor={selectedExtractor}
              onSelectExtractor={setSelectedExtractor}
              formatExtractorLabel={(name) => {
                const job = jobs.find(j => j.extractor === name)
                return job?.extractor_display_name || formatAudioExtractorName(name)
              }}
            />
          </div>
          {/* Rating Control */}
          <div className="flex-shrink-0">
            <RatingControl
              rating={rating}
              onRatingChange={onRatingChange}
              submitting={submittingRating}
              error={ratingError}
              averageRating={averageRating}
              totalRatings={totalRatings}
            />
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {loadingRawResult || loadingAnnotations ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-2">
                <Loader2 className="h-6 w-6 animate-spin" />
                <span>Loading extraction data...</span>
              </div>
            </div>
          ) : (selectedExtractor === 'whisper-openai' && segments && segments.length > 0) || ((selectedExtractor === 'aws-transcribe' || selectedExtractor === 'assemblyai') && rawResult) ? (
            <div className="flex-1 overflow-auto w-full h-full">
              <FormattedRawResult
                data={selectedExtractor === 'whisper-openai' ? segments : rawResult}
                extractor={selectedExtractor}
                annotations={annotations}
                onCreate={onCreateAnnotation}
                onDelete={onDeleteAnnotation}
                currentSegment={currentSegment}
                extractionJobUuid={selectedJob?.uuid}
                highlightedAnnotationId={highlightedAnnotationId}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              {selectedExtractor === 'whisper-openai' ? 'No segments available' : 'Raw result not available'}
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

