'use client'

import React from 'react'
import { Card, CardContent } from '../../../../../../../components/ui/card'
import { AlertCircle, Loader2 } from 'lucide-react'
import { ImageExtractionJob, ImageAnnotation } from '../../../../../../../services/imageApi'
import { ExtractorSelector } from '../../../../../../../pdf/components/extractors/ExtractorSelector'
import { RatingControl } from '../../../../../../../pdf/components/extractors/RatingControl'
import AnnotatableText from '../../../../../../../components/AnnotatableText'

interface ImageAnnotationTabProps {
  hasSuccessfulExtractors: boolean
  imageUrl: string
  imageLoading: boolean
  imageError: string | null
  imageFilename?: string
  token: string | null
  selectedExtractor: string
  setSelectedExtractor: (extractor: string) => void
  jobs: ImageExtractionJob[]
  rating: number
  onRatingChange: (rating: number) => void
  submittingRating: boolean
  ratingError: string | null
  averageRating?: number
  totalRatings?: number
  content: string
  contentLoading: boolean
  mappedAnnotations: Array<{ id: string; start: number; end: number; comment: string }>
  onCreateAnnotation: (args: { start: number; end: number; comment: string }) => Promise<{ id?: string } | void>
  onDeleteAnnotation: (id: string) => Promise<void>
  loadingAnnotations: boolean
  highlightedAnnotationId?: string | null
}

export function ImageAnnotationTab({
  hasSuccessfulExtractors,
  imageUrl,
  imageLoading,
  imageError,
  imageFilename,
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
              content,
              contentLoading,
              mappedAnnotations,
              onCreateAnnotation,
              onDeleteAnnotation,
              loadingAnnotations,
              highlightedAnnotationId,
}: ImageAnnotationTabProps) {
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
        {/* Left Column: Image Viewer */}
        <Card className="overflow-hidden flex flex-col h-full">
          <div className="bg-gray-50 px-4 py-3 border-b">
            <h3 className="text-sm font-semibold text-foreground">Image</h3>
          </div>
          <CardContent className="flex-1 overflow-auto p-4">
            {imageLoading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : imageError ? (
              <div className="flex flex-col items-center justify-center h-full text-red-600">
                <AlertCircle className="h-6 w-6 mb-2" />
                <p>{imageError}</p>
              </div>
            ) : imageUrl ? (
              <div className="w-full h-full flex items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={imageUrl} alt={imageFilename} className="w-full h-auto object-contain" />
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <AlertCircle className="h-12 w-12" />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right Column: Content and Controls */}
        <Card className="overflow-hidden flex flex-col h-full">
          {/* Header: Controls */}
          <div className="bg-gray-50 px-4 py-3 border-b flex items-center justify-between gap-2 min-w-0 overflow-hidden">
            {/* Extractor Selector */}
            <div className="flex-shrink-0">
              <ExtractorSelector
                extractionJobs={jobs as any}
                selectedExtractor={selectedExtractor}
                onSelectExtractor={setSelectedExtractor}
                formatExtractorLabel={(name) => name}
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
          <CardContent className="flex-1 min-h-0 overflow-auto p-4">
            {contentLoading || loadingAnnotations ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span>Loading extraction data...</span>
                </div>
              </div>
            ) : content ? (
              <div className="prose max-w-none">
                <AnnotatableText
                  text={content}
                  initialAnnotations={mappedAnnotations}
                  onCreate={onCreateAnnotation}
                  onDelete={onDeleteAnnotation}
                  highlightedAnnotationId={highlightedAnnotationId}
                />
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                No content available
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

